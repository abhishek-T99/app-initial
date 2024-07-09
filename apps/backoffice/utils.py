import jinja2

from core.config import config


def get_formatted_permissions(permissions):
    permission_mapping = {}
    for permission in permissions:
        group_name = permission[0]
        if group_name not in permission_mapping:
            permission_mapping[group_name] = []
        permission_mapping[group_name].append(permission[1])
    return permission_mapping


def render_template(template_name, **kwargs):
    templateLoader = jinja2.FileSystemLoader(searchpath=config.base_dir + "/templates")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(template_name)
    outputText = template.render(**kwargs)
    return outputText


class DummyEmailService:
    def send(self, topic, message):
        print(
            f"Not sending message to topic '{topic}': {message} because I am just a dummy."
        )

dummyemailservice = DummyEmailService()
