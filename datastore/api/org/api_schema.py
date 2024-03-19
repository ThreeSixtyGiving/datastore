from drf_spectacular.views import SpectacularAPIView


INCLUDE_PATHS = set(
    [
        "/api/experimental/org/{org_id}/grants_made/",
        "/api/experimental/org/{org_id}/grants_received/",
        "/api/experimental/org/{org_id}/",
        "/api/experimental/org/",
        "/api/experimental/grant/{grant_id}/",
    ]
)


def only_include_org_api_endpoints(endpoints):
    """
    Only keep endpoints in the schema which are relevent to the Org Grants API.
    """
    kept_endpoints = [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if path in INCLUDE_PATHS
    ]
    return kept_endpoints


SPECTACULAR_SETTINGS = {
    "TITLE": "360 Giving Organisation Grants API",
    "DESCRIPTION": "Describe grants made and recieved by organisations.",
    "VERSION": "0.0.1",
    "COMPONENT_SPLIT_REQUEST": True,
    "PREPROCESSING_HOOKS": [__name__ + "." + only_include_org_api_endpoints.__name__],
}


class APISchemaView(SpectacularAPIView):
    custom_settings = SPECTACULAR_SETTINGS
