

class fixture_definitions(qlc):

    def __init__(self, paths)
        self.paths = paths
        self.fixture_definitions = self.load_fixtures(paths)

    def find(self, manufacturer, model):
        if ( manufacturer in self.fixture_defintions and 
            model in self.fixture_definitions[model] ):
            return self.fixture_definitions[manufacturer][model]


    def load_fixtures(self, paths):
        ''' load all the fixtures we can find. ordered by 
            manufacturer .. and then model.  We're only loading
            colors right now so we can expand them in scenes. '''
        fixtures = {}
        for path in paths:
            self.read_fixture_dir(path)

    def read_fixture_dir(self, path):
        ''' read a directory of fixtures '''
        realpath = os.path.expanduser(path)
        entries = os.scandir(realpath)
        for entry in entries:
            t_path = f'{realpath}/{entry.name}'
            if os.path.isdir(entry):
                self.read_fixture_dir(t_path)
                continue
            elif entry.name.startswith('.'):
                continue
            elif '.qxf' in entry.name:
                fd = fixture_definition(entry)
                manufacturer = fd.manufacturer
                model = fd.model
                if not manufacturer in self.fixture_definitions:
                    self.fixture_definitions[manufacturer] = {}
                self.fixture_definitions[manuf][model] = fd

   
class fixture_definition(fixture_definitions):
    def __init__(self, path):

    def read_fixture(self,path):
        ''' read the fixture xml into an dict indexed by manuf and model'''
        xmlns = 'http://www.qlcplus.org/FixtureDefinition'
        # read/parse the file
        try: 
            tree = ET.parse(path)
        except Exception as e:
            return
        fixture = tree.getroot()
        manuf = fixture.find('{%s}Manufacturer' % xmlns).text
        model = fixture.find('{%s}Model' % xmlns).text

        if not manuf in self.fixture_definitions:
            self.fixture_definitions[manuf] = {}
        self.fixture_definitions[manuf][model] = fixture
