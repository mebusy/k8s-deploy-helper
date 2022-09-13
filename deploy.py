#!python3

# pip3 install pyyaml --user

import sys
import os
import subprocess
import yaml
import inspect
from src.loadconf import loadconf
from src.bashparser import parsebashvar
from src.ColorPrint import ColorPrint as _cp

def getImageTag( env, server ):
    tag = "{}-{}:latest".format( server["name"], env )
    return tag

def getKubectlCmd( env, server, path_k8s_conf = None ):
    if path_k8s_conf == "" or not path_k8s_conf:
        return "kubectl -n {}".format( server["namespace"] )
    else:
        return "kubectl --kubeconfig {} -n {}".format( path_k8s_conf, server["namespace"] )

def openSystemCmd( cmd ):
    result = subprocess.run( cmd , shell=True )
    if result.returncode != 0:
        _cp.print_fail (str(result))
        sys.exit(1)



def call_build( env, server ):
    """build server image """
    server_name, server_path  = server["name"], server["path"]

    tag = getImageTag(env, server)
    _cp.print_info( "·················· building image {}".format( tag ) )

    cwd = os.path.dirname(os.path.abspath(__file__))
    path_docker_file = os.path.join( cwd, server_path , "image" )

    cmd = " ".join( ["docker build -t", tag, path_docker_file ] )

    result = subprocess.run( cmd , shell=True )
    if result.returncode != 0:
        _cp.print_fail (str(result))
        sys.exit(1)

def call_upload_tc( env, server ):
    """upload image to k8s, and restart service """
    call_upload_local( env, server, bLocal = False )

def call_upload_local( env, server, bLocal = True ):
    """upload image to local k8s, and restart service """

    server_name, server_path  = server["name"], server["path"]
    _cp.print_info( "·················· uploading && restarting {}".format( server_name ) )

    # tag
    cmd = "docker tag {imgtag} {ecr_root}/{imgtag}".format( imgtag= getImageTag( env, server ), ecr_root= ecr_root )
    openSystemCmd(cmd)
    # upload to aws
    cmd = "docker push {ecr_root}/{imgtag}".format( imgtag= getImageTag( env, server ), ecr_root= ecr_root )
    openSystemCmd(cmd)

    # namespace = server["namespace"]
    cmd = "{} rollout restart deployment {}".format( getKubectlCmd( env,server, kubeconf ), server_name )
    result = subprocess.run( cmd , shell=True )
    if result.returncode != 0:
        _cp.print_fail (str(result))
        sys.exit(1)


def deprecated_call_deploy_aws( env, server ):
    """apply modified svc|deploy|ingress yaml to aws
    \t\t\t(not necessarily `deploy` again if nothing changed) """
    return call_deploy_local( env, server, bLocal = False )

def call_deploy_tc( env, server ):
    """apply modified svc|deploy|ingress yaml to tencent cloud
    \t\t\t(not necessarily `deploy` again if nothing changed) """
    return call_deploy_local( env, server, bLocal = False )


def call_deploy_local( env, server, bLocal = True ):
    """apply modified svc|deploy|ingress yaml to local k8s """

    server_name, server_path  = server["name"], server["path"]
    _cp.print_info( "·················· deploying server {}".format( server_name ) )

    container_environment_vars = server["env-local"] if bLocal else server["env"]

    platform = "local"  # fake
    if not bLocal :
        # get real platform
        # fname = inspect.currentframe().f_code.co_name
        fname = inspect.currentframe().f_back.f_code.co_name
        platform = fname[ fname .rfind("_") + 1 : ] 

    print( f"{platform}" )

    # ecr_root
    other_server_info = {
        "image-path" : "{}/{}".format( ecr_root , getImageTag(env, server) ),
    }

    # get tmpl
    path_yaml = os.path.join( os.path.dirname(__file__), "./k8s-yamls/svc-deploy-tmpl.yaml" )
    with open( path_yaml ) as fp:
        temp = fp.read()

    if bLocal :
        # local deployment use conf `ingress-host-local`
        key = "ingress-host"
        server[key] = server[ key+"-local" ]

    infos = { **other_server_info, **server }
    data = temp.format( **infos )

    obj = yaml.load(data, Loader=yaml.SafeLoader )
    for item in obj["items"]:
        kind = item["kind"]
        if kind == "Deployment":
            # insert environment variables
            spec = item["spec"]
            spec_tmpl_spec = spec["template"]["spec"]
            container0 = spec_tmpl_spec["containers"][0]
            container0["env"] = container_environment_vars
            # local k8s, `imagePullPolicy` sould be `Never
            # if bLocal:
            #     for container in spec_tmpl_spec["containers"]:
            #         container["imagePullPolicy"] = "Never"
            if platform == "tc" : # tencent cloud + imagePullSecrets
                # you need goto tencent cloud console / namespace to issue `qcloudregistrykey`
                spec_tmpl_spec[ "imagePullSecrets" ] = [ { "name":"qcloudregistrykey" } ]

        if kind == "Ingress":
            # add ingress annotations
            ingress_anno_key = "ingress-annotations" if not bLocal else "ingress-annotations-local"
            if ingress_anno_key in server:
                item["metadata"]["annotations"] = server[ ingress_anno_key ]
            # for 1 domain name, multiple server in local environment
            if bLocal:
                item["spec"]["rules"][0]["http"]["paths"][0]["path"] = "/" + servername + '(/|$)(.*)'
            # if host not be specified
            if item["spec"]["rules"][0]["host"] is None:
                # to keep `kubectl apply` consistent
                del item["spec"]["rules"][0]["host"]

    path_dst_yaml = os.path.join( TMP_FOLD, "{}-{}.yaml".format( server_name, env ) )
    with open( path_dst_yaml, "w") as fp:
        yaml.dump( obj, fp ) #, allow_unicode=True ) 

    # debug yaml file
    if False :
        with open(path_dst_yaml) as fp:
            print(fp.read() )
        return

    cmd = '{} apply -f {} '.format( getKubectlCmd( env,server, kubeconf ) , path_dst_yaml ) 
    result = subprocess.run( cmd , shell=True )
    if result.returncode != 0:
        _cp.print_fail (str(result))
        sys.exit(1)

TMP_FOLD=".tmp"


"""
TODO AWS ingress annotations, 
item["metadata"]["annotations"]

    annotations:
      kubernetes.io/ingress.class: alb # aws
      alb.ingress.kubernetes.io/scheme: internet-facing # aws internet ingress
      ???
"""

if __name__ == '__main__':
    _cp.print_pass("=="*50)
    os.environ["KUBECONFIG"] = ""  # preventing conflicting with other k8s env

    # load main config
    ENV, servers, cluster, cluster_local = loadconf()

    # get all available actions , that is, methods startswith `call_`
    actions = {}
    from inspect import getmembers, isfunction
    all_moduel_funcs = getmembers( sys.modules[__name__] , isfunction)
    for func_name, func in all_moduel_funcs:
        if func_name.startswith( "call_" ):
            if ENV=="prod" and func_name.endswith( "_local" )  :  # prevent deploy local in prod branch 
                continue

            actions[ func_name[ 5: ] ] = func.__doc__

    # if True:
    #     sys.exit(2)



    # debug
    _cp.print_info( "available servers:" )
    for servername , server in servers.items():
        print("\t", servername) # , server
    _cp.print_info( "available actions:")

    for actionname , desc in actions.items():
        print( "\t", actionname, ": ", desc )
    
    print("")
    if len(sys.argv) < 3:
        _cp.print_info( "usage: ./deploy.py <server-name> <action> [,<action>...]" )
        _cp.print_info(
        """
        examples:
        # build local image for server `dot-iap`
        ./deploy.py  dot-iap build

        # deploy server `dot-iap` to local k8s
        ./deploy.py dot-iap deploy_local

        # build && deploy to local k8s
        ./deploy.py dot-iap build deploy_local

        # build && upload to aws && restart related pods
        ./deploy.py all build upload_aws
        """

        )
        sys.exit(1)

    # start....
    if ENV not in ["dev","prod"]:
        _cp.print_fail( "conf incorrect, ENV should be `dev`, or `prod`" ) 
        sys.exit(1)

    servername = sys.argv[1]
    # validate servername
    if servername != "all" and  servername not in servers:
        _cp.print_fail( "{} is not a valid server".format(servername) )
        sys.exit(2)
    

    if not os.path.exists( TMP_FOLD ):
        os.makedirs( TMP_FOLD )

    # which server to operate
    servernames_to_operate = servers.keys() # all servers ?
    if servername != "all":
        servernames_to_operate = [ servername ]  # only specific server

    for servername in servernames_to_operate:
        server = servers[ servername ]
        # actions 
        for action in sys.argv[2:]:
            # validate action
            if action not in actions:
                _cp.print_fail( "{} is not a valid action".format(action) )
                sys.exit(3)

            # change local/production setting
            bLocal = action.endswith( "local" ) # DEFINE what is local
            ecr_root = cluster_local["ecr_root"] if bLocal else cluster["ecr_root"]
            kubeconf = "./kubeconfs/local.conf" if bLocal else "./kubeconfs/prod.conf"

            # call action function
            func_name = "call_" + action
            locals()[func_name]( ENV, server )

    _cp.print_pass ('all done')

