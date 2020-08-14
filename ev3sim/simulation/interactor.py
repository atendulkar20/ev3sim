class IInteractor:

    constants: dict

    def __init__(self, **kwargs):
        pass

    def startUp(self):
        pass

    # tick returns a boolean, which is true if the script should end.
    def tick(self, tick) -> bool:
        return False

    def afterPhysics(self):
        pass

    def tearDown(self):
        pass

    # Handles events pumped from pygame.
    def handleEvent(self, event):
        pass

def fromOptions(options):
    if 'filename' in options:
        import yaml
        from ev3sim.file_helper import find_abs
        fname = find_abs(options['filename'])
        with open(fname, 'r') as f:
            config = yaml.safe_load(f)
            return fromOptions(config)
    if 'class_path' not in options:
        raise ValueError("Your options has no 'class_path' or 'filename' entry (Or the file you reference has no 'class_path' entry')")
    mname, cname = options['class_path'].rsplit('.', 1)
    import importlib
    klass = getattr(importlib.import_module(mname), cname)
    return klass(*options.get('args', []), **options.get('kwargs', {}))
