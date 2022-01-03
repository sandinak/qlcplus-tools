#! /usr/bin/env python

'''
============================================================================
Title: manage qlc showfile
Description:
QLC Libraries
============================================================================
NOTES/TODO:
- need to refine the searches to be attribute aware instead of defining them discretely.
- need to setup add/delete for things (Functions, Heads, etc)
- allow import of colors for creation?
- handle 'light' colors for heads that dont' have a white LED
- add 'preset' position creation for all fixtures. 
'''

import logging as log
import xml.etree.ElementTree as ET
from xml.dom import XML_NAMESPACE, minidom
import sys
import copy
import pprint
import urllib.parse
import re
import os



# colors 
# http://www.webriti.com/wp-content/uploads/2012/01/rgb-color-wheel-lg.jpg
# colors for white.
# TODO: Make a set w/o white called rgb
FIXTURE_PATHS = [ 
    '/Applications/QLC+.app/Contents/Resources/Fixtures',
    '~/Library/Application Support/QLC+/Fixtures' 
    ]
rgbw = {        #shortname               R    G    B    W
    'Red':      { 'n':'R',    'rgbw': [255,   0,   0,   0], },
    'Green':    { 'n':'G',    'rgbw': [  0, 255,   0,   0], },
    'Blue':     { 'n':'B',    'rgbw': [  0,   0, 255,   0], },
    'Yellow':   { 'n':'Y',    'rgbw': [255, 255,   0,   0], },
    'Cyan':     { 'n':'C',    'rgbw': [  0, 255, 255,   0], },
    'Magenta':  { 'n':'M',    'rgbw': [255,   0, 255,   0], },
    'Violet':   { 'n':'V',    'rgbw': [128,   0, 255,   0], },
    'All':      { 'n':'A',    'rgbw': [255, 255, 255, 255], },
    'Rasp':     { 'n':'Ra',   'rgbw': [255,   0, 128,   0], },
    'Orange':   { 'n':'Or',   'rgbw': [255, 128,   0,   0], },
    'Ocean':    { 'n':'Oc',   'rgbw': [  0, 128, 128,   0], },
    'Turqoise': { 'n':'T',    'rgbw': [  0, 255, 128,   0], },
    'Purple':   { 'n':'P',    'rgbw': [128,   0, 255,   0], },
    'Pink':     { 'n':'Pk',   'rgbw': [255,   0, 128,   0], },
    'White':    { 'n':'W',    'rgbw': [  0,   0,  0,  255], },

    # with white
    'Red+W':    { 'n':'RW',   'rgbw': [255,   0,   0, 255], },
    'Green+W':  { 'n':'GW',   'rgbw': [0,   255,   0, 255], },
    'Blue+W':   { 'n':'BW',   'rgbw': [0,     0, 255, 255], },
    'Yellow+W': { 'n':'YW',   'rgbw': [255, 255,   0, 255], },
    'Cyan+W':   { 'n':'CW',   'rgbw': [0,   255, 255, 255], },
    'Red+W':    { 'n':'MW',   'rgbw': [255,   0, 255, 255], },
    'Purple+W': { 'n':'PW',   'rgbw': [128,   0, 255, 255], },
    'Rasp+W':   { 'n':'RaW',  'rgbw': [255,   0, 128, 255], },
    'Orange+W': { 'n':'OrW',  'rgbw': [255, 128,   0, 255], },
    'Ocean+W':  { 'n':'OcW',  'rgbw': [  0, 128, 128, 255], },
    'Turqoise+W': { 'n':'TW', 'rgbw': [  0, 255, 128, 255], },
    'Purple+W': { 'n':'PW',   'rgbw': [128,   0, 255, 255], },
    'Pink+W':   { 'n':'PkW',  'rgbw': [255,   0, 128, 255], },
}
# because names are such random things
RGB_ALTERNATES = {
    'Cyan': 'Light Blue'
}

SPOT_ON_CHANNELS = [
    'Master Dimmer',
    'Strobe/Shutter',
    'Shutter',
    'Dimmer',
    'Intensity',
    'Shutter',
]

MOVEMENT_CHANNEL_NAMES = [
    'Pan',
    'Level',
    'Horizontal',
    'Tilt',
    'Vertical'
]

# there's really only 1 here as we don't know the relative 
# horizontal positions, nor the total vertical deflection;
# however having the preset to start with will help minimize
# movements from this position .. rather than starting with 0,0
# TODO: eventually it'd be good to pre-compute some positions by the 
#       head PAN Max and Tilt Max .. however we dont' know which way 
#       the heads turn or starting position .. so V is more reliable 
#       than H... be nice to incporporate some of the work from 
#       dmx_followspot which describes position, height, etc.
BASE_POSITIONS = {
            #    H       V DMX Values, not angle.
    'Base':   [ 128,    128] ,
}



def match(items,item):
    for i in items:
        if i == item:
            return i

def _strip(elem):
    for elem in elem.iter():
        if(elem.text):
            elem.text = elem.text.strip()
        if(elem.tail):
            elem.tail = elem.tail.strip()

def intersection(lst1, lst2): 
    return list(set(lst1) & set(lst2))


BLANK_WORKSPACE = '''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Workspace>
<Workspace xmlns="http://www.qlcplus.org/Workspace" CurrentWindow="FixtureManager">
 <Creator>
  <Name>Q Light Controller Plus</Name>
  <Version>4.12.3</Version>
  <Author>Branson Matheson</Author>
 </Creator>
 <Engine>
  <InputOutputMap>
   <Universe Name="Universe 1" ID="0"/>
   <Universe Name="Universe 2" ID="1"/>
   <Universe Name="Universe 3" ID="2"/>
   <Universe Name="Universe 4" ID="3"/>
  </InputOutputMap>
 </Engine>
 <VirtualConsole>
  <Frame Caption="">
   <Appearance>
    <FrameStyle>None</FrameStyle>
    <ForegroundColor>Default</ForegroundColor>
    <BackgroundColor>Default</BackgroundColor>
    <BackgroundImage>None</BackgroundImage>
    <Font>Default</Font>
   </Appearance>
  </Frame>
  <Properties>
   <Size Width="1920" Height="1080"/>
   <GrandMaster ChannelMode="Intensity" ValueMode="Reduce" SliderMode="Normal"/>
  </Properties>
 </VirtualConsole>
 <SimpleDesk>
  <Engine/>
 </SimpleDesk>
</Workspace>
EOF
'''.strip()

ENCODING = 'UTF-8'
DOCTYPE='''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Workspace>
'''.strip()

class QLC():
    def __init__(self, file=None):
        ''' setup a working QLC space '''
        self.fixture_definitions = FixtureDefinitions(FIXTURE_PATHS)
        self.workspace = Workspace(file)

    def expand_fixture_group_capabilities(self):
        for fg in self.workspace.engine.fixture_groups:
            if len(fg.heads.items) == 0:
                continue

            self.generate_color_scenes(fg)
            self.generate_capability_scenes(fg)

    def generate_universes(self, universes):
        us = self.workspace.engine.inputoutputmap
        # these are mapped as shown
        id = 0
        for u in universes:
            this_u = us.find_by_id(id)
            if not this_u:
                self.generate_universe(us, u)


    def generate_fixture_group(self, fg):
        fgs = self.workspace.engine.fixture_groups
        Name = fg.get('name')
        efg = fgs.find_by_name(fg.get('name'))
        if not efg:
            this_fg = ET.SubElement(fgs.root, "FixtureGroup")
            ID = str(fgs.next_id())
            this_fg.set('ID',ID)
        else: 
            this_fg = efg

    def generate_fixtures(self,fixtures):
        output_ips = dict()
        fs = self.workspace.engine.fixtures
        for fixture in fixtures:
            output_ip = fixture.get('output_ip')
            output_ip_id = None
            # generate default output_ip_uni if not set
            if output_ip:
                if output_ip not in output_ips:
                    output_ips[output_ip] = []
                output_ips[output_ip].append(fixture)
                output_ip_uni = fixture.get('output_uni' or str(len(output_ips[output_ip])+1))

            # find existing fixture
            Name = fixture.get('name')
            ef = fs.find_by_name(Name)
            if not ef:
                this_f = ET.SubElement(fs.root, "Fixture")
                ID = str(fs.next_id())
                this_f.set('ID', ID)
                this_f.set('Name', Name)
            else:
                this_f = ef

            # find fixture definition
            Model = fixture.get('model')
            this_fd = self.fixture_definitions.find_by_model(Model)
            if not this_fd:
                raise Exception(f'Unable to find fixture definition for {Model}')
            this_f.set('Manufacturer', this_fd.get('Manufacturer'))
            this_f.set('Model', this_fd.get('Model'))
            
            # find mode
            Mode = fixture.get('Mode')
            if Mode:
                fd_mode = this_fd.modes.find_by_name(Mode)
                if not fd_mode:
                    raise Exception(f'Unable to find mode {Mode} in fixture def: {Model}') 
            elif len(this_fd.modes.items) >= 1:
                fd_mode = this_fd.modes.items[0]
            else:
                raise Exception(f'No mode defined for fixture definition {Model}')
            this_f.set('Mode', Mode)

        def generate_universe(self,us):
            # find U
            us = self.workspace.engine.inputoutputmap
            if 'u' in fixture:
                this_u = us.find_by_id(fixture.get('u'))
            elif 'u_name' in fixture: 
                this_u = us.find_by_name(fixture.get('name'))
            elif 'ip_address' in fixture:
                this_u = us.find_by_output(
                    fixture.get('ip_address'),fixture.get('output_id') or output_ip_uni )

            if not this_u:
                this_u = us.generate({
                    'ID': str(us.last_ud()+1),
                    'Name': fixture.get('u_name') or fixture.get('name'),
                })

            u_id = this_u.get('ID')
                
            # setup output to ArtNet if needed
            if output_ip:
                this_output = this_u.root.find(this_u, "{%s}Output")
                if not this_output:
                    this_output = ET.SubElement(this_u.root,"Output")
                this_output.set('Plugin', fixture.get('plugin') or 'ArtNet')
                # TODO: map this by known IP?
                this_output.set('Line', fixture.get('line') or '2')
                this_output_p = this_output.root.find('PluginParamters')
                if not this_output_p:
                    this_output_p = ET.SubElement(this_output_p.root, "{%s}PluginParameters")
                    this_output_p.set('outputIP', output_ip)
                    this_output_p.set('outputUni', output_ip_uni)
                
        

    def generate_color_scenes(self, fg):
        ''' this is now fixture independent... which means that groups
            can have more than one fixture type and it will try still do the 
            right thing finding the intersections of colors across all the 
            fixtures '''
        Type = 'Scene' 
        Path = '/'.join(['Colors', fg.name])
        for color_name, color_data in rgbw.items():  
            Name = '/'.join([Path, color_name])
            # generate fval by head
            fvals = {}
            for head in fg.heads: 
                # get fixture, if we can't find it.. skip
                fixture = self.workspace.engine.fixtures.find_by_id(head.fixture_id)
                if fixture.mode == None: 
                    continue

                # we skip undefined fixtures or pixel fixtures 
                definition = self.fixture_definitions.find_by_fixture(fixture)
                if definition == None or 'Pixels' in definition.type:
                    continue

                mode_channels = definition.modes.find_by_name(fixture.mode).mode_channels

                fval = []
                if 'Red' in mode_channels.names:
                    # this is an RGB Head
                    red, green, blue, white = color_data.get('rgbw')
                    for mc in mode_channels:
                        mc_num = mc.number 
                        mc_name = mc.name 
                        if mc_name == 'Intensity' or mc_name == 'Dimmer':
                            fval.append(f'{mc_num},255')
                        elif 'Red' in mc_name:
                            fval.append(f'{mc_num},{red}')
                        elif 'Green' in mc_name:
                            fval.append(f'{mc_num},{green}')
                        elif 'Blue' in mc_name:
                            fval.append(f'{mc_num},{blue}')
                        elif 'White' in mc_name:
                            fval.append(f'{mc_num},{white}')

                elif color_channels := intersection(mode_channels.names, ['Colour','Color']):
                    # this is a color wheel head
                    channel = definition.channels.find_by_name(color_channels[0])
                    # see if we can match to a predefined color
                    if color_name in RGB_ALTERNATES:
                        color_name = RGB_ALTERNATES[color_name]
                    if capability := channel.capabilities.find_by_name(color_name):
                        cval = capability.min
                        for mc in mode_channels.items:
                            if mc.name in SPOT_ON_CHANNELS:
                                fval.append(f'{mc.number},255')
                            elif mc.name == channel.name:
                                fval.append(f'{mc.number},{cval}')

                # assemble the fvals for this head
                if len(fval) > 0:
                    fvals[fixture.id] = ','.join(fval)

            # create the scene if all heads in the group are accounted for 
            if len(fg.heads.items) == len(fvals):
                self.function(
                    Type = Type,
                    Path = Path,
                    Name = Name,
                    FixtureVals = fvals)

    def generate_capability_scenes(self, fg):
        ''' take each expandable channel and make scenes for the capabilities
            NOTE: this one does NOT work across heads.. so is only gonna work when the 
            heads are all the same. '''

        # first lets determine if this FG has all the same definition and mode
        fixture_definition = None
        mode = None
        for head in fg.heads:
            # identify this fixture.
            fixture = self.workspace.engine.fixtures.find_by_id(head.fixture)

            # get the definition and determine if it matches
            d = self.fixture_definitions.find_by_fixture(fixture)
            if d == None:
                return
            elif ( fixture_definition == None ):
                fixture_definition = d
            elif ( fixture_definition != d ):
                return

            # determine mode matches for all
            if fixture_definition:
                m = fixture_definition.modes.find_by_name(fixture.mode)
            if ( mode == None ): 
                mode = m
            elif mode != m:
                return

            # if we have no mode or channels .. moot.
            if mode == None or mode.mode_channels == None:
                return
        
        # now get the capability channels to expand for this fixture mode. 
        # we identify the right ones by the channel groups we support.
        for mode_channel in mode.mode_channels:

            # get the corresponding channel configuration for this mode_channel
            channel = fixture_definition.channels.find_by_name(mode_channel.name)

            # if more than 1 capability that's not the base color .. expand
            if mode_channel.name == 'Color' or len(channel.capabilities.items) == 1:
                continue

            # normalize the name so it doesn't become part of the path
            channel_name = channel.name.replace('/','+')
            Path = '/'.join(['FixtureGroups', fg.name, channel_name])

            # get capabilities for this channel
            for capability in channel.capabilities:

                # set the normalized scene name and capability value
                capability_name = capability.name.replace('/','+')
                Name = '/'.join([Path, capability.name ])

                # generate fvals for this capability on this channel
                fvals = {}
                for head in fg.heads:
                    fval = []
                    for mc in mode.mode_channels:
                        if channel.name in mc.name:
                            fval.append(f'{mc.number},{capability.min}')
                    fvals[head.fixture] = ','.join(fval)
                
                # generate scene
                self.function(
                    Type = 'Scene',
                    Path = Path,
                    Name = Name,
                    FixtureVals = fvals)
            
        # if moving head, generate base position for this fixture 
        if fixture_definition.type  == 'Moving Head': 
            Path = '/'.join(['Positions', fg.name])
            for name, pos in BASE_POSITIONS.items():
                h,v = pos
                Name = '/'.join([Path, name ])
                fvals = {}
                for head in fg.heads:
                    fval = []
                    for mc in mode.mode_channels:
                        channel = fixture_definition.channels.find_by_name(mc.name)
                        # no consistency among fixtures here.. frustrating. 
                        if channel.group == 'Pan':
                            fval.append(f'{mc.number},{h}')
                        elif channel.group == 'Tilt':
                            fval.append(f'{mc.number},{v}')
                    fvals[head.fixture] = ','.join(fval)
                
                # generate scene
                self.function(
                    Type = 'Scene',
                    Path = Path,
                    Name = Name,
                    FixtureVals = fvals)
            

    

    # TODO: extrapolate this into the actual classes 
    def function(self, **kwargs):
        functions = self.workspace.engine.functions
        
        Name = kwargs.get('Name')
        ID = kwargs.get('ID') 
        Type = kwargs.get('Type')
        Path = kwargs.get('Path')

        # go find if we can, ID is most significant
        func = None
        if ID:
            func = functions.find_by_id(ID)
        if not func and Name: 
            func = functions.find_by_name(Name)

        # if not create root element
        if not func:
            this_func = ET.SubElement(functions.root, "Function")
            ID = str(functions.next_id())
            this_func.set('ID', ID)
        else:
            ID = func.id
            this_func = func.root

        # set/update primatives
        this_func.set('Name', Name)
        this_func.set('Type', Type)

        # optional
        if Path:
           this_func.set('Path', Path)

        if Type == 'Script':
            self.f_script(this_func, **kwargs)
        elif Type == 'Scene': 
            fvals = kwargs.get('FixtureVals')
            self.f_scene(this_func, **kwargs)

    def f_script(self, f, **kwargs):
        
        self.fattr_speed(f, **kwargs)
        default_direction = 'Forward'
        if direction := kwargs.get('Direction') or default_direction:
            d = f.find('{%s}Direction' % Workspace.xmlns)
            if d == None:
                d = ET.SubElement(f, 'Direction')
            d.text = direction

        default_runorder = 'Loop'
        if runorder := kwargs.get('RunOrder') or default_runorder:
            r = f.find('{%s}RunOrder' % Workspace.xmlns)
            if r == None:
                r = ET.SubElement(f, 'RunOrder')
            r.text = runorder

        if kwargs.get('Command'):
            c = f.find('{%s}Command' % Workspace.xmlns)
            if c == None:
                c = ET.SubElement(f, 'Command')
            command = urllib.parse.quote(kwargs.get('Command'), safe='')
            c.text = command

    # create a scene
    def f_scene(self, f, **kwargs):
        fvals = kwargs.get('FixtureVals')
        self.fattr_speed(f, **kwargs)

        # set fixture vals
        fvs = f.findall('{%s}FixtureVal' % Workspace.xmlns)
        existing_fv_ids = []
        for fv in fvs:
            fid = fv.get('ID')
            existing_fv_ids.append(fid)
            # remove it if not part of the group, else 
            # update value
            if not fid in fvals:
                f.remove(fv)
            else:
                fv.text = fvals[fid]

        # update it if it's not there
        for fid, cstr in fvals.items():
            if fid not in existing_fv_ids:
                this_fv = ET.SubElement(f,'FixtureVal')
                this_fv.set('ID', fid)
                this_fv.text = cstr        


    def fattr_speed(self,f,**kwargs):
        default_speed = {
            'FadeIn': '0',
            'FadeOout': '0',
            'Duration': '0'
        } 
        if speed := kwargs.get('Speed') or default_speed:
            s = f.find('{%s}Speed' % Workspace.xmlns)
            if s == None:
                s = ET.SubElement(f, 'Speed')
            for k, v in speed.items():
                s.set(k, v)

    
class Workspace(QLC):
    xmlns = 'http://www.qlcplus.org/Workspace'
    def __init__(self, file):
        ''' setup class '''
        # expand common targets
        ET.register_namespace('', self.xmlns)

        self.file = file

        if self.file:
            self.tree = ET.parse(self.file)
            self.root = self.tree.getroot()
        else:
            self.root = ET.fromstring(BLANK_WORKSPACE)
        
        self.creator = Creator(self.root)
        self.engine = Engine(self.root)
   
    def _gen_text(self):
        _strip(self.root)
        rough_bytes = ET.tostring(self.root) #, 'utf-8')
        # fix DOCTYPE
        reparsed = minidom.parseString(rough_bytes)
        xml = reparsed.toprettyxml(indent=' ')
        xml = xml.replace('<?xml version="1.0" ?>', DOCTYPE)
        return xml
    
    def dump(self):
        self.text = self._gen_text()
        print(self.text)

    def write(self, file=None):
        out = file or self.file
        self.text = self._gen_text()
        f = open(out, 'w')
        f.write(self.text)
        f.close()

class Creator(Workspace):
    def __init__(self, root):
        self.root = root.find('{%s}%s' % (Workspace.xmlns, type(self).__name__))
        self.name = self.root.find('{%s}Name' % Workspace.xmlns).text
        self.version = self.root.find('{%s}Version' % Workspace.xmlns).text
        self.author = self.root.find('{%s}Author' % Workspace.xmlns).text

class Engine(Workspace):
    def __init__(self, root):
        self.root = root.find('{%s}%s' % (Workspace.xmlns, type(self).__name__))
        self.inputoutputmap =  InputOutputMap(self.root)
        self.fixtures = Fixtures(self.root)
        self.fixture_groups = FixtureGroups(self.root)
        self.functions = Functions(self.root)

class InputOutputMap(Engine):
    def __init__(self, root):
        self.root = root.find('{%s}%s' % (Workspace.xmlns, type(self).__name__))
        self.universes = Universes(self.root)

class Universes(InputOutputMap):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Universe' % Workspace.xmlns):
            self.items.append(Universe(item))

        self.names = list(map(lambda x: x.name, self.items))

        # map addresses
        self.u_by_output_ip = dict()
        for u in self.items:
            if u.output.output_ip:
                self.u_by_output_ip[u.output_ip] = u

    def add(self, u):
        self.items.append(Universe.generate(root, u))

    
    def find_by_output(self, output_ip, output_uni=None):
        u = self.u_by_ouput_ip.get(output_ip)
        if u:
            for o_ip_u in self.u_by_output_ip[output_ip]:
                if o_ip_u.output_uni == output_uni:
                    return o_ip_u


    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i
        
    def find_by_id(self, fid):
        for i in self.items:
            if i.id == fid:
                return i
    
    def last_id(self):
        r = 0
        for item in self.items:
            if int(item.id) > r:
                r = int(item.i)
        return r

    def __iter__(self):
        return iter(self.items)

class Universe(Universes):
    def __init__(self,root):
        self.name = root.get('Name')
        if root.find('{%s}Input'):
            self.input = Input(root)
        if root.find('{%s}Output'):
            self.output = Output(root)
            self.output_uni = self.output_uni
            self.output_ip = self.output_ip

  
    def generate(self, root, u):
        this_u = ET.SubElement(root, "{%s}Universe" % Workspace.xmlns)
        this_u.set('ID', u.get('ID'))
        this_u.set('Name', u.get('Name'))
        if u.get('outputIP') and u.get('outputUni'):
            Output.generate(this_u, u)

class Input(Universe):
    def __init__(self,root):
        self.root = root.find('{%s}Input' % Workspace.xmlns)
        self.plugin = self.root.get('Plugin')
        self.line = self.root.get('Line')


# TODO: this all assumes artnet, make agnostic
class Output(Universe):
    def __init__(self,root):
        self.root = root.find('{%s}Input' % Workspace.xmlns)
        self.plugin = self.root.get('Plugin')
        self.line = self.root.get('Line')
        parameters = self.root.find('{%s}PluginParameters' % Workspace.xmlns)
        self.outputUni = parameters.get('outputUni')
        self.outputIP = parameters.get('outputIP')

    def generate(self,root, u):
        this_output = ET.SubElement(root,"Output")
        this_output.set('Plugin', 'ArtNet')
        # TODO: map this by known IP?
        this_output.set('Line', u.get('Line') or '2')
        this_output_p = ET.SubElement(this_output.root, "{%s}PluginParameters" % Workspace.xmlns)
        this_output_p.set('outputIP', u.get('outputIP'))
        this_output_p.set('outputUni', u.get('outputUni'))

class Fixtures(Engine):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Fixture' % Workspace.xmlns):
            self.items.append(Fixture(item))

        self.names = list(map(lambda x: x.name, self.items))
        
    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i
        
    def find_by_id(self, fid):
        for i in self.items:
            if i.id == fid:
                return i
        
    def __iter__(self):
        return iter(self.items)
    

class Fixture(Fixtures):
    def __init__(self, root):
        self.manufacturer = root.find('{%s}Manufacturer' % Workspace.xmlns).text
        self.model = root.find('{%s}Model' % Workspace.xmlns).text
        self.mode = root.find('{%s}Mode' % Workspace.xmlns).text
        self.id = root.find('{%s}ID' % Workspace.xmlns).text
        self.name = root.find('{%s}Name' % Workspace.xmlns).text
        self.universe = root.find('{%s}Universe' % Workspace.xmlns).text
        self.address = root.find('{%s}Address' % Workspace.xmlns).text
        self.channels = root.find('{%s}Channels' % Workspace.xmlns).text
    

class FixtureGroups(Engine):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}FixtureGroup' % Workspace.xmlns):
            self.items.append(FixtureGroup(item))

        self.names = list(map(lambda x: x.name, self.items))
            
    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i
        
    def find_by_id(self, fid):
        for i in self.items:
            if i.id == fid:
                return i

    def __iter__(self):
        return iter(self.items)
    
 
class FixtureGroup(FixtureGroups):
    def __init__(self, root):
        self.name = root.find('{%s}Name' % Workspace.xmlns).text
        self.id = root.get('ID')
        self.size = Size(root)
        self.heads = Heads(root)
    

class Size(FixtureGroup):
    def __init__(self, root):
        self.root = root.find('{%s}Size' % Workspace.xmlns)
        self.x = self.root.get('X')
        self.y = self.root.get('y')


class Heads(FixtureGroup):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Head' % Workspace.xmlns):
            self.items.append(Head(item))

class Head(Heads):
    def __init__(self, root):
        self.x = root.get('X')
        self.y = root.get('Y')
        self.fixture = root.get('Fixture')
        self.fixture_id = root.get('Fixture')

class Functions(Engine):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Function' % Workspace.xmlns):
            self.items.append(Function(item))

        self.names = list(map(lambda x: x.name, self.items))

        self.last_id = 0
        for item in self.items:
            if int(item.id) > self.last_id:
                self.last_id = int(item.id)

    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i

    def find_by_path(self, path):
        for i in self.items:
            if i.path == path:
                return i

    def find_by_id(self, id):
        for i in self.items:
            if i.id == id:
                return i
    
    def next_id(self):
        self.last_id += 1
        return self.last_id

    def __iter__(self):
        return iter(self.items) 

class Function(Functions):
    def __init__(self, root):
        self.root = root
        self.id = root.get('ID')
        self.type = root.get('Type')
        self.name = root.get('Name')
        self.path = root.get('Path')
        self.speed = Speed(root)
        if 'Scene' in  self.type:
            self.config = Scene(root)

class Scene(Function):
    def __init__(self, root):
        self.fixture_vals = FixtureVals(root)
        self.speed = Speed(root)

class FixtureVals(Scene):
    def __init__(self,root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}FixtureVal' % Workspace.xmlns):
            self.items.append(FixtureVal(item))

    def __iter__(self):
        return iter(self.items) 
        
class FixtureVal(FixtureVals):
    def __init__(self, root):
        self.id = root.get('ID')
        self.data = root.text

class Speed(Function):
    def __init__(self, root):
        self.root = root.find('{%s}Speed' % Workspace.xmlns)
        if self.root: 
            self.fadein = self.root.get('FadeIn') 
            self.fadeout = self.root.get('FadeOut') 
            self.duration = self.root.get('Duration')
        else: 
            self.fadein = '0'
            self.fadeout = '0'
            self.duration = '0'

class FixtureDefinitions(QLC):
    def __init__(self, paths):
        self.paths = paths
        self.items = dict()
        self.fd_by_model = dict()
        for path in paths:
            self.read_fixture_dir(path)
    
    def read_fixture_dir(self,path):
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
                fd = FixtureDefinition(entry)
                if manufacturer := fd.manufacturer:
                    model = fd.model
                else:
                    continue
                # list by manufacturer and model
                if not manufacturer in self.items:
                    self.items[manufacturer] = {}
                self.items[manufacturer][model] = fd
                # list by model
                if not model in self.fd_by_model:
                    self.fd_by_model[model] = []
                self.fd_by_model[model].append(fd)


    def find_by_manufacturer_model(self, manufacturer, model):
        if ( manufacturer in self.items and model in self.items[manufacturer] ):
            return self.items[manufacturer][model]

    def find_by_fixture(self, fixture):
        return self.find_by_manufacturer_model(fixture.manufacturer, fixture.model)

    def find_by_model(self, model):
        return self.fd_by_model.get(model)

    def __iter__(self):
        return iter(self.items)

class FixtureDefinition(FixtureDefinitions):
    # for all fixture definitions..
    xmlns = 'http://www.qlcplus.org/FixtureDefinition'

    def __init__(self, path):
        ''' read the fixture xml into an dict indexed by manuf and model'''
        # read/parse the file
        ET.register_namespace('', FixtureDefinition.xmlns)

        try: 
            tree = ET.parse(path)
        except Exception:
            self.manufacturer = None
            return None
        self.root = tree.getroot()

        # set accessors
        self.manufacturer = self.root.find('{%s}Manufacturer' % FixtureDefinition.xmlns).text
        self.model = self.root.find('{%s}Model' % FixtureDefinition.xmlns).text
        self.type = self.root.find('{%s}Type' % FixtureDefinition.xmlns).text

        self.channels = Channels(self.root)
        self.modes = Modes(self.root)
        self.physical = Physical(self.root)
        
class Physical(FixtureDefinition):
    ''' extract channels and return a list '''
    def __init__(self, root):
        self.item = root.findall('{%s}Physical' % FixtureDefinition.xmlns)
        # get layout
        if self.item:
            layout = self.item[0].find('{%s}Layout' % FixtureDefinition.xmlns)
            if layout:
                self.layout.width = layout.get('Width')
                self.layout.height = layout.get('Height')

            # get dimensions
            dimensions = self.item[0].find('{%s}Dimensions' % FixtureDefinition.xmlns)
            if dimensions: 
                self.dimensions.width = dimensions.get('Width')
                self.dimensions.height = dimensions.get('Height')
                self.dimensions.depth = dimensions.get('Depth')
                self.dimensions.weight = dimensions.get('weight')



 

class Channels(FixtureDefinition):
    ''' extract channels and return a list '''
    def __init__(self, root):
        self.items = []
        for item in root.findall('{%s}Channel' % FixtureDefinition.xmlns):
            self.items.append(Channel(item))

        self.names = list(map(lambda x: x.name, self.items))

    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i

    def find(self, name):
        return self.find_by_name(name)

    def __iter__(self):
        return iter(self.items)

class Channel(Channels):
    def __init__(self, root):
        self.root = root
        # create accessors
        self.name = root.get('Name')
        self.capabilities = Capabilities(root)
        group = root.find('{%s}Group' % FixtureDefinition.xmlns)
        if group != None:
            self.group = group.text
        else:
            self.group = None

class Capabilities(Channel):
    def __init__(self, root):
        self.items = []
        for item in root.findall('{%s}Capability' % FixtureDefinition.xmlns):
            self.items.append(Capability(item))

        self.names = list(map(lambda x: x.name, self.items))

    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i

    def find(self, name):
        self.find_by_name(name)

    def __iter__(self):
        return iter(self.items)

class Capability(Capabilities):
    def __init__(self, root):
        self.root = root
        self.name = root.text
        self.min = root.get('Min')
        self.max = root.get('Max')

class Modes(Channel):
    def __init__(self, root):
        self.items = []
        for item in root.findall('{%s}Mode' % FixtureDefinition.xmlns):
            self.items.append(Mode(item))

        self.names = list(map(lambda x: x.name, self.items))

    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i
    
    def find(self, name):
        return self.find_by_name(name)

    def __iter__(self):
        return iter(self.items)

class Mode(Modes):
    def __init__(self, root):
        self.root = root
        self.name = root.get('Name')
        self.mode_channels = ModeChannels(root)

class ModeChannels(Mode):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Channel' % FixtureDefinition.xmlns):
            self.items.append(ModeChannel(item))
        
        self.names = list(map(lambda x: x.name, self.items))
        
    def find_by_name(self, name):
        for i in self.items:
            if i.name == name:
                return i
    
    def find_by_number(self, number):
        for i in self.items:
            if i.number == number:
                return i

    def find(self, name):
        return self.find_by_name(name)

    def __iter__(self):
        return iter(self.items)

class ModeChannel(ModeChannels):
    def __init__(self, root):
        self.root = root
        self.name = root.text
        self.number = root.get('Number')
        
        