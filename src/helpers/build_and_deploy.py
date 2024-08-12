import json
import yaml
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Params:
    def __init__(self):
        __name = None
        __version = None
        __digest = None
        __registry = None
        __context = None
        __env = []
        __filters = {}

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def version(self):
        return self.__version

    @version.setter
    def version(self, version):
        self.__version = version

    @property
    def digest(self):
        return self.__digest

    @digest.setter
    def digest(self, digest):
        self.__digest = digest

    @property
    def registry(self):
        return self.__registry

    @registry.setter
    def registry(self, registry):
        self.__registry = registry

    @property
    def context(self):
        return self.__context

    @context.setter
    def context(self, context):
        self.__context = context

    @property
    def envs(self):
        return self.__envs

    @envs.setter
    def envs(self, envs):
        self.__envs = envs

    @property
    def filters(self):
        return self.__filters

    @filters.setter
    def filters(self, filters):
        self.__filters = filters


def load_func_config():
    params = Params()
    logger.info("reading func parameters")
    with open("func.yaml") as f:
        try:
            y = yaml.safe_load(f)
        except yaml.YAMLError as err:
            logger.critical(err)

    params.name = y['name']
    params.version = y['version']
    params.digest = y['digest']
    params.registry = y['registry']
    params.context = y['context']
    params.envs = y['run']['envs']
    params.filters = y['filters']
    return params
    

def render_trigger(params: Params):
    logger.info("reading trigger template")
    with open("templates/trigger.yaml") as f:
        try:
            y = yaml.safe_load(f)
        except yaml.YAMLError as err:
            logger.critical(err)

    y['metadata']['name'] = f"{params.name}-trigger"
    y['metadata']['namespace'] = f"context-{params.context}"
    y['spec']['broker'] = f"context-broker-{params.context}"
    y['spec']['delivery']['deadLetterSink']['ref']['name'] = f"context-broker-{params.context}-dead-letter"
    y['spec']['delivery']['deadLetterSink']['ref']['namespace'] = f"context-{params.context}"
    y['spec']['filters'] = params.filters
    y['spec']['subscriber']['ref']['name'] = params.name
    y['spec']['subscriber']['ref']['namespace'] = f"context-{params.context}"

    logger.info("writing trigger.yaml")
    with open("trigger.yaml", "w") as f:
        yaml.dump(y, f, default_flow_style=False)

def render_kservice(params: Params):
    logger.info("reading kservice template")
    with open("templates/kservice.yaml") as f:
        try:
            y = yaml.safe_load(f)
        except yaml.YAMLError as err:
            logger.critical(err)

    y['metadata']['name'] = params.name
    y['metadata']['namespace'] = f"context-{params.context}"
    y['spec']['template']['spec']['containers'][0]['image'] = f"{params.registry}/{params.name}:{params.version}@{params.digest}"
    y['spec']['template']['spec']['containers'][0]['env'] = params.envs

    logger.info("writing kservice.yaml")
    with open("kservice.yaml", "w") as f:
        yaml.dump(y, f, default_flow_style=False)

def renderResources():
    logger.info("rendering k8s resources")
    params = load_func_config()
    render_trigger(params)
    render_kservice(params)

if __name__ == "__main__":
    renderResources()
