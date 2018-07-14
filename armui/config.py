import yaml

yamlfile = 'C:/etc/arm/arm.yaml'

with open(yamlfile, "r") as f:
    cfg = yaml.load(f)
