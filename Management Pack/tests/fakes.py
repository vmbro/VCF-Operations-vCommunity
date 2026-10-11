#  Copyright 2026 VCF Operations vCommunity Management Pack
"""A fake VCF Operations, shared by the KPI tests."""


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        return self.body


class FakeSuiteApi:
    """A fake VCF Operations Suite API.

    samples:    {resource id: {stat key: [samples]}}, for the stats queries.
    properties: {resource id: {property key: value}}, for the properties query.
    resources:  {resource kind: [(resource id, name, MoRef id)]}, for the resources query.
    """

    def __init__(self, samples=None, status_code=200, properties=None, resources=None):
        self.samples = samples or {}
        self.properties = properties or {}
        self.resources = resources or {}
        self.status_code = status_code
        self.requests = 0
        self.paths = []

    def paged_post(self, path, key, json):
        self.paths.append(path)
        resource_list = [
            {"identifier": resource_id, "resourceKey": {"name": name, "resourceIdentifiers": [
                {"identifierType": {"name": "VMEntityObjectID"}, "value": moid}]}}
            for kind in json["resourceKind"] for resource_id, name, moid in self.resources.get(kind, [])
        ]
        return {key: resource_list}

    def post(self, path, json):
        self.requests += 1
        self.paths.append(path)
        if "propertyKeys" in json:
            return self._properties(json)
        values = []
        for resource_id in json["resourceId"]:
            stats = [
                {"statKey": {"key": key}, "timestamps": list(range(len(data))), "data": data}
                for key, data in self.samples.get(resource_id, {}).items() if key in json["statKey"]
            ]
            values.append({"resourceId": resource_id, "stat-list": {"stat": stats}})
        return FakeResponse({"values": values}, self.status_code)

    def _properties(self, json):
        values = []
        for resource_id in json["resourceIds"]:
            contents = [
                {"statKey": key, "timestamps": [0], "values": [value]}
                for key, value in self.properties.get(resource_id, {}).items() if key in json["propertyKeys"]
            ]
            values.append({"resourceId": resource_id, "property-contents": {"property-content": contents}})
        return FakeResponse({"values": values}, self.status_code)


class FakeObject:
    """An SDK object. Like the real one, it has no get_id(): the resource id comes from utils/ops_stats.py."""

    def __init__(self, name):
        self.name = name
        self.metrics = {}

    def with_metric(self, key, value):
        self.metrics[key] = value


class FakeMoRef:
    def __init__(self, mo_id, vm=(), host=()):
        self._moId = mo_id
        self.vm = list(vm)
        self.host = list(host)
