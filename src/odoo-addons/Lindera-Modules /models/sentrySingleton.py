import sentry_sdk


class sentrySingleton:
    class __sentrySingleton:
        def __init__(self, url):
            self.Client = sentry_sdk.init(url)
    instance = None
    def __init__(self, url):
        if not sentrySingleton.instance:
            sentrySingleton.instance = sentrySingleton.__sentrySingleton(url)
        else:
            sentrySingleton.instance.val = url
    def __getattr__(self, name):
        return getattr(self.instance, name)
