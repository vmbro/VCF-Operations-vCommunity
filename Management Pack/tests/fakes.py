#  Copyright 2026 VCF Operations vCommunity Management Pack
"""A fake VCF Operations, shared by the KPI tests."""


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def json(self):
        return self.body


class FakeSuiteApi:
    """Answers stats queries from {resource id: {stat key: [samples]}}."""

    def __init__(self, samples, status_code=200):
        self.samples = samples
        self.status_code = status_code
        self.requests = 0

    def post(self, path, json):
        self.requests += 1
        values = []
        for resource_id in json["resourceId"]:
            stats = [
                {"statKey": {"key": key}, "timestamps": list(range(len(data))), "data": data}
                for key, data in self.samples.get(resource_id, {}).items() if key in json["statKey"]
            ]
            values.append({"resourceId": resource_id, "stat-list": {"stat": stats}})
        return FakeResponse({"values": values}, self.status_code)


class FakeObject:
    def __init__(self, resource_id):
        self.resource_id = resource_id
        self.metrics = {}

    def get_id(self):
        return self.resource_id

    def with_metric(self, key, value):
        self.metrics[key] = value


class FakeMoRef:
    def __init__(self, mo_id, vm=(), host=()):
        self._moId = mo_id
        self.vm = list(vm)
        self.host = list(host)
