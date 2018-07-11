import yaml

yamlfile = '/etc/arm/arm.yaml'

with open(yamlfile, "r") as f:
    cfg = yaml.load(f)
