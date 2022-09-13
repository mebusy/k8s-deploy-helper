
import yaml
from collections import defaultdict

def loadconf():
    ## define custom tag handler
    def join(loader, node):
        seq = loader.construct_sequence(node)
        return ''.join([str(i) for i in seq])

    ## register the tag handler
    yaml.add_constructor('!join', join)

    # load conf
    with open("./conf.yaml") as fp:
        conf = yaml.load(fp.read() , Loader=yaml.FullLoader )  # , Loader=yaml.SafeLoader
    
    servers = {}

    for server in conf["servers"]:
        server = defaultdict(str, server) # default dict
        # print (server)
        server_name = server["name"]
        server_path = server["path"]
        namespace = server["namespace"]
        port = server["port"]
        ingress_host = server["ingress-host"]
        if server_name != "" and server_path != "" and namespace != "" and port != "" \
            and ingress_host != "":
            servers[server_name] = server

    return conf["ENV"], servers, conf["cluster"], conf["cluster-local"]

