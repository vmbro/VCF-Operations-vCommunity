
## How does VCF Operations vCommunity Management Pack Work ? 
Custom Management Packs created using the VCF Operations Integration SDK have some additional requirements. First, their Adapter Instances need to run on a Cloud Proxy for data collection. Once you've  installed the Management Pack and created an Adapter Instance, the Cloud Proxy tries to access the adapter container registry to pull the docker image configuration.  After that docker image will install the necessary files that are defined in the DockerFile then the PAK file will be initialized for the data collection process.

If the Cloud Proxy has container registry access (access to the Internet), users can simply install the Management Pack then create Adapter Instances.  There is no need for any other modifications by users in VCF Operations.

![Adapter-Topology](Documentation-Images/screenshots/VCF_Operations_vCommunity_Topology.svg)

## How Integration SDK Works ?

A Cloud Proxy collector process managing adapter containers, which each correspond to one adapter instance. Within each container is the REST server and the adapter process. The ```Commands.cfg``` file tells the REST server how to run the adapter process for each endpoint.

![Adapter-Topology](Documentation-Images/screenshots/VCF_Operations_Integration_SDK_Topology.png)
