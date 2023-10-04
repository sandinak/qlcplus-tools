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

import logging 
import xml.etree.ElementTree as ET
from xml.dom import XML_NAMESPACE, minidom
import sys
import copy
import pprint
import urllib.parse
import re
import os
import xlsxwriter
import pandas as pd

logger = logging.getLogger(__name__)

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
    'White':    { 'n':'W',    'rgbw': [  0,   0,   0,  255], },
    'Flesh':    { 'n':'F',    'rgbw': [245, 204, 176,  0], },
    'IntOnly':  { 'n':'IO',   'rgbw': [  0,   0,  0,  0],   },

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
    'Flesh+W':  { 'n':'FW',   'rgbw': [245, 204, 176, 255], },
}
# because names are such random things
RGB_ALTERNATES = {
    'Cyan': 'Light Blue'
}

SPOT_ON_CHANNELS = [
    'master dimmer',
    'spot-master dimmer',
    'strobe/shutter',
    'shutter',
    'dimmer',
    'intensity',
    'dim/strobe'
]

# NOTE: this is case sensitive.
SPOT_COLORWHEEL_NAMES = [
    'Colour',
    'Color',
    'Color wheel',
    'Color Wheel',
    'Spot-Color Wheel',
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
    'Base':   [ 128,    128],
    '0':      [ 0,      0],
}

# regexes
size_re = re.compile(r'X:(\d+) Y:(\d+)')
fixture_re = re.compile(r'^(.*) H:(\d+)') # A:(\d+) U:(\d+)$')
# fixture_re = re.compile(r'^(.*)\sH:(\d+)')


def match(items,item):
    for i in items:
        if i == item:
            return i

def _strip(elem):
    for elem in elem.iter():
        if(elem.text):
            elem.text = str(elem.text).strip()
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
        self.output_ips = dict()

    def expand_fixture_group_capabilities(self):
        for fg in self.workspace.engine.fixture_groups.items:
            Name = fg.name
            logging.info(f'processing fixture group: {Name}')
            if len(fg.heads.items) == 0:
                continue

            self.generate_color_scenes(fg)
            self.generate_capability_scenes(fg)

    def generate_universes(self, universes):
        us = self.workspace.engine.inputoutputmap.universes
        # these are mapped as shown
        for u in universes:
            id = u.get('id')
            this_u = us.find_by_id(id)
            if  this_u:
                this_u.update(u)
            else:
                us.add(u)


    def export_fixture_groups(self, path):
        fgs = self.workspace.engine.fixture_groups
        sheets = []
        workbook = xlsxwriter.Workbook(path)
        bold = workbook.add_format({'bold': True})
        bold_c = workbook.add_format({'bold': True, 'align': 'center'})
        for fg in fgs:
            worksheet = workbook.add_worksheet(fg.name)
            worksheet.write(0,0,f'Fixture Group: {fg.name}', bold)
                            
            # generate the matrix for this sheet
            # m: y,x
            size = fg.size
            # NOTE: y and x are REVERSED coming from QLC,
            # so if this seems odd it's to handle that strange case.
            s_x = int(size.x or "0") + 1 
            s_y = int(size.y or "0") + 1

            # test heads to make sure we have the right size
            for head in fg.heads:
                if int(head.y) > s_y:
                    s_y = int(head.y)
                if int(head.x) > s_x:
                    s_x = int(head.x)
                    
            worksheet.write(1,0,f'X:{s_x} Y:{s_y}', bold)
            logger.info(f"initalizing table %s: {s_y},{s_x}" % fg.name)
            m = []
            # setup the grid
            for y in range(0, s_y+2):
                worksheet.write(y+2, 0, y+1, bold_c)
                m.append(['' for _ in range(0,s_x+2)])

            for x in range(0, s_x+1):
                worksheet.write(1, x+1, x+1, bold_c )
                for y in range(0, s_y+1):
                    worksheet.write(x, y, '', )

            max_w = 0
            for head in fg.heads:
                # TODO do we need the universe and such or just the name here. 
                # fname = "%s: u:%d a: %d" % (head.fixture.name, head.fixture.universe, head.fixture.channels)
                logger.debug(f"looking for fixture id {head.fixture}")
                fixture = self.workspace.engine.fixtures.find_by_id(head.fixture)                
                if fixture: 
                    fname = fixture.name
                    logger.info(f"storing fixture {fname} ({head.id}) at {head.y},{head.x} in {s_y},{s_x}")
                    # qlc plus displays relative to 1 vs 0
                    h_id = int(head.id) + 1
                    f_addr = int(fixture.address) + 1
                    f_uni = int(fixture.universe) + 1
                    m_name =f"{fname} H:{h_id}"
                    if len(m_name) > max_w:
                        max_w = len(m_name)
                    m[int(head.y)][int(head.x)] = f"{m_name}" # \n{m_addr}"

            # set widths
            for c in range(0, s_x+1):
                worksheet.set_column(c, c, max_w+1)

            worksheet.add_table(2, 1, 2+s_y, 1+s_x, { 'header_row': False, 'data': m})
        workbook.close()


    def extract_fixture_from_cell(self, data):
        if isinstance(data, str):
            data = data.replace('\n',' ')
            r = fixture_re.search(data)
            if not r:
                logger.error(f"unlable to match fixture data\n===\n{data}\n===")
                sys.exit(1)
            name, head = r.groups()
            f = self.workspace.engine.fixtures.find_by_name(name)
            if not f:
                logger.error(f"unable to match fixture to {name}")
                sys.exit(1)
            return f, head
        return False, None


    def extract_size_from_cell(self,data):
        r = size_re.search(data)
        if not r: 
            logger.error(f"unlable to match size data {data}")
            sys.exit(1)
            
        s_x, s_y = r.groups() 
        return int(s_y), int(s_x)

    def extract_fg_from_sheet(self, sheet):
        s_x, s_y = self.extract_size_from_cell(sheet.iat[0,0])
        logger.debug(f"extracting sheet size {s_x},{s_y}")
        heads = []
        for x in range(0, s_x):
            for y in range(0, s_y):
                try: 
                    data = sheet.iat[x+1,y+1]
                except:
                    continue
                logger.debug(f"extracting {x},{y}: {data}")
                f, head = self.extract_fixture_from_cell(data)
                if f: 
                    # generate head xml, remember reversed
                    heads.append({
                        'x': str(int(y)),
                        'y': str(int(x)),
                        'f_id': f.id, 
                        'head': str(int(head) -1),
                    })
        return s_x, s_y, heads 
            
    def import_fixture_groups(self, path):
        worksheet = pd.ExcelFile(path)
        # each sheet name represents a fixture group
        for sheet_name in worksheet.sheet_names:
            sheet = worksheet.parse(sheet_name)
            s_x, s_y, heads = self.extract_fg_from_sheet(sheet)
            fg = {
                'name': sheet_name,
                'size_x': s_x,
                'size_y': s_y,
                'heads': heads
            }
            self.update_fixture_group(fg)

    def update_fixture_group(self, fg):
        fgs = self.workspace.engine.fixture_groups
        Name = fg.get('name')
        efg = fgs.find_by_name(Name)
        # if it exists, we use that fgid and delete the old one
        if efg: 
            ID = str(efg.id)
            fgs.root.remove(efg.root)
        else:
            # else we generate a new one
            ID = str(fgs.next_id())

        this_fg = ET.SubElement(fgs.root, "FixtureGroup")
        logger.info(f'generating fg {Name} {ID}')
        this_name = ET.SubElement(this_fg, 'Name')
        this_name.text = Name
        this_fg.set('ID',str(ID))
        this_size = ET.SubElement(this_fg, 'Size')
        this_size.set('X', str(fg.get('size_y')))
        this_size.set('Y', str(fg.get('size_x')))
        for head in fg.get('heads'):
            this_head = ET.SubElement(this_fg, 'Head')
            this_head.set('X',str(head.get('x')))
            this_head.set('Y',str(head.get('y')))
            this_head.set('Fixture',str(head.get('f_id')))
            this_head.text = head.get('head')

    def generate_fixtures(self,fixtures):
        fs = self.workspace.engine.fixtures
        for fixture in fixtures:
            logger.debug('generatng fixture %s ' % pprint.pformat(fixture))
           
            # find or create fixture
            ef = fs.find_by_name(fixture.get('name'))
            if not ef:
                this_f = ET.SubElement(fs.root, "Fixture")
                ID = str(fs.next_id())
                ET.SubElement(this_f, "ID").text = ID
            else:
                this_f = ef.root
            ET.SubElement(this_f, "Name").text = fixture.get('name')

            # find fixture definition and set Manufacturer
            this_f_model = fixture.get('model')
            this_fd = self.fixture_definitions.find_by_model(this_f_model)[0]
            if not this_fd:
                raise Exception(f'Unable to find fixture definition for {this_f_model}')
            ET.SubElement(this_f, "Manufacturer").text = this_fd.manufacturer
            ET.SubElement(this_f, "Model").text = this_fd.model
            ET.SubElement(this_f, "Channels").text = str(len(this_fd.channels.items))
            ET.SubElement(this_f, "Address").text = str(fixture.get('a'))
            
            # find mode, required
            if fixture.get('mode'):
                this_f_mode = fixture.get('mode')
                fd_mode = this_fd.modes.find_by_name(this_f_mode)
                if not Mode:
                    raise Exception(f'Unable to find mode {this_f_mode} in fixture def: {this_f_model}') 
            elif len(this_fd.modes.items) == 1:
                fd_mode = this_fd.modes.items[0]
            else:
                raise Exception(f'No mode defined for fixture definition {this_f_model}')
            ET.SubElement(this_f, "Mode").text = fd_mode.name

            # TODO eventually make this smart
            u = fixture.get('u')
            ET.SubElement(this_f, "Universe").text = u

      
    def _sort_fval(self,fval):
        i = iter(fval.split(','))
        d = dict(zip(i, i))
        l = []
        for k in sorted(d, key=lambda item: int(item)):
            l.append(k)
            l.append(d[k])
        r = ','.join(l)
        return r

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
            fixtures = {}
            for head in fg.heads: 
                # get fixture, if we can't find it.. skip
                fixture = self.workspace.engine.fixtures.find_by_id(head.fixture_id)
                if not fixture:
                    print(f"  FAIL: no fixture found for {head.fixture_id}")
                if fixture and fixture.mode == None: 
                    print(f"  FAIL: no fixture mode for {fixture.name}")
                    continue
                fixtures[fixture.id] = True

                # we skip undefined fixtures or pixel fixtures 
                fixture_definition = self.fixture_definitions.find_by_fixture(fixture)
                if fixture_definition == None or 'Pixels' in fixture_definition.type:
                    continue
                fixture_mode = fixture_definition.modes.find_by_name(fixture.mode)
                if fixture_mode.heads.count:
                    # if we have more than one head .. find the channels for that head
                    mode_channels = fixture_mode.heads.find_by_id(head.id).mode_channels
                else:
                    # if not use all the channels for the 
                    mode_channels = fixture_mode.mode_channels

                fval = []
                if any('Red' in s for s in mode_channels.names):
                    # this is an RGB Head
                    red, green, blue, white = color_data.get('rgbw')
                    for mode_channel in mode_channels:
                        channel = mode_channel.channel
                        channel_name = channel.name.lower()
                        # if multi head .. wash must be in the name
                        if ( 'intensity' in channel_name or 'dimmer' in channel_name):
                            fval.append(f'{mode_channel.number},255')
                        elif 'red' in channel_name:
                            fval.append(f'{mode_channel.number},{red}')
                        elif 'green' in channel_name:
                            fval.append(f'{mode_channel.number},{green}')
                        elif 'blue' in channel_name:
                            fval.append(f'{mode_channel.number},{blue}')
                        elif 'white' in channel_name:
                            fval.append(f'{mode_channel.number},{white}')

                if color_channels := intersection(mode_channels.names, SPOT_COLORWHEEL_NAMES):
                    # this has a color wheel head
                    color_channel = fixture_definition.channels.find_by_name(color_channels[0])
                    # see if we can match to a predefined color
                    if color_name in RGB_ALTERNATES:
                        color_name = RGB_ALTERNATES[color_name]

                    if capability := color_channel.capabilities.find_by_name(color_name):
                        cval = capability.min
                        for mode_channel in mode_channels:
                            channel = mode_channel.channel
                            channel_name = channel.name.lower()
                            color_channel_name = color_channel.name.lower()
                            # if multi-head .. 'spot' must be in the name
                            if ( 'intensity' in channel_name or 'dimmer' in channel_name
                                  or channel_name in SPOT_ON_CHANNELS):
                                fval.append(f'{mode_channel.number},255')
                            elif channel_name == color_channel_name:
                                fval.append(f'{mode_channel.number},{cval}')

                # assemble the fvals for this head
                if len(fval) > 0:
                    if fixture.id in fvals:
                        fvals[fixture.id] = self._sort_fval((fvals[fixture.id] + ',%s' % ','.join(fval)))
                    else: 
                        fvals[fixture.id] = ','.join(fval)

            # create the scene if all heads in the group are accounted for 
            if len(fixtures) == len(fvals):
                print(f"  adding {Name}")
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
        capabilities = {}
        moving_head = False
        fixtures = dict()
        for head in fg.heads:

            # get fixture, if we can't find it.. skip
            fixture = self.workspace.engine.fixtures.find_by_id(head.fixture_id)
            if not fixture:
                print(f"  FAIL: no fixture found for {head.fixture_id}")
            if fixture and fixture.mode == None: 
                print(f"  FAIL: no fixture mode for {fixture.name}")
                continue
            fixtures[fixture.id] = True

            # we skip undefined fixtures or pixel fixtures 
            fixture_definition = self.fixture_definitions.find_by_fixture(fixture)
            if fixture_definition == None or 'Pixels' in fixture_definition.type:
                continue
            mode = fixture_definition.modes.find_by_name(fixture.mode)
            if mode.heads.count:
                mode_channels = mode.heads.find_by_id(head.id).mode_channels
            else:
                mode_channels = fixture_definition.modes.find_by_name(fixture.mode).mode_channels

            # now get the capability channels to expand for this fixture mode. 
            # we identify the right ones by the channel groups we support.
            for mode_channel in mode_channels:
                channel = mode_channel.channel
                # normalize the name so it doesn't become part of the path
                # for any channel with capabilities, we make scenes
                if channel.capabilities:
                    channel_name = channel.name.replace('/','+')
                    Path = '/'.join(['Capabilties', fg.name, channel_name])
                    for capability in channel.capabilities:
                        if capability.name: 
                            fval=[]
                            # set the normalized scene name and capability value
                            Name = '/'.join([Path, capability.name.replace('/','+') ])
                            fval.append(f'{mode_channel.number},{capability.min}')
                            if Name not in capabilities:
                                logger.info(f'adding {Name} to capabilities')
                                capabilities[Name] = { 'fvals': {} }
                            capabilities[Name]['Path'] = Path
                            capabilities[Name]['fvals'][fixture.id] = ','.join(fval)

     
            # if moving head, generate base positions for this fixture 
            if fixture_definition.type == 'Moving Head': 
                Path = '/'.join(['Positions', fg.name])

                for name, pos in BASE_POSITIONS.items():
                    h,v = pos
                    Name = '/'.join([Path, name ])
                    fval = []
                    for mode_channel in mode_channels: 
                        channel = mode_channel.channel
                        if channel.group == 'Pan' or channel.name == 'Pan':
                            fval.append(f'{mode_channel.number},{h}')
                        elif channel.group == 'Tilt' or channel.name == 'Tilt':
                            fval.append(f'{mode_channel.number},{v}')
                    if fval: 
                        if Name not in capabilities:
                            logger.info(f'adding movement {Name} to capabilities')
                            capabilities[Name] = { 'fvals' : {} }
                        capabilities[Name]['Path'] = Path
                        logger.debug(f"adding {head.fixture} {fval} to {Name}")
                        capabilities[Name]['fvals'][fixture.id] = ','.join(fval)
                    
        # generate scenes
        for Name,c in capabilities.items():
            self.function(
                Type = 'Scene',
                Name = Name,
                Path = c['Path'],
                FixtureVals = c['fvals'])

    # TODO: extrapolate this into the actual classes 
    def function(self, **kwargs):
        functions = self.workspace.engine.functions
        
        Name = kwargs.get('Name')
        ID = kwargs.get('ID') 
        Type = kwargs.get('Type')
        Path = kwargs.get('Path')

        logger.debug(f'generating function {Name} at {Path}')

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
        logger.debug(f'loading {file}')

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
        if not self.root:
            self.root = ET.SubElement(root, type(self).__name__)
        self.inputoutputmap =  InputOutputMap(self.root)
        self.fixtures = Fixtures(self.root)
        self.fixture_groups = FixtureGroups(self.root)
        self.functions = Functions(self.root)
    

class InputOutputMap(Engine):
    def __init__(self, root):
        self.root = root.find('{%s}%s' % (Workspace.xmlns, type(self).__name__))
        if not self.root:
            self.root = ET.SubElement(root, type(self).__name__)
        self.universes = Universes(self.root)

class Universes(InputOutputMap):
    def __init__(self, root):
        self.root = root
        self.items = []
        for item in root.findall('{%s}Universe' % Workspace.xmlns):
            self.items.append(Universe(item))

        self._next_id = 0
        self.names = list(map(lambda x: x.name, self.items))
        self.ids = list(map(lambda x: x.id, self.items))
        for id in self.ids:
            if int(id) > self._next_id:
                self._next_id = int(id)

        # map addresses
        self.u_by_output_ip = dict()
        for u in self.items:
            if u.output and u.output.output_ip:
                self.u_by_output_ip[u.output.output_ip] = u

    def add(self, u):
        self.items.append(Universe(self.root, u))


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
            if int(i.id) == int(fid):
                return i
    
    def next_id(self):
        self._next_id +=1
        return self._next_id
    
    def __iter__(self):
        return iter(self.items)

class Universe(Universes):
    def __init__(self, root, u=None):
        self.channels = [None] * 512
        self.input = None
        self.output = None
        if u:
            self.output_ip = u.get('ipaddr')
            self.output_u = u.get('artnet_u')
            self.id = str(u.get('id'))
            self.name = u.get('name')
            logger.debug('generatng universe %s' % pprint.pformat(u))
            self.root = ET.SubElement(root, "{%s}Universe" % Workspace.xmlns)
            self.root.set('ID', self.id)
            self.root.set('Name',self.name)
            if self.output_ip:
                self.output = Output(self.root, u)
        else: 
            # read
            self.root = root
            self.name = root.get('Name')
            self.id = root.get('ID')
            if root.find('{%s}Input' % Workspace.xmlns):
                self.input = Input(self.root, u)
            if root.find('{%s}Output' % Workspace.xmlns):
                self.output = Output(self.root, u)

    def update(self, u):
        self.root.set('Name',u.get('name'))
        if u.get('ipaddr') and u.get('artnet_u') and self.output:
            self.output.update(u)

    def allocate(self, channel, f_id):
        self.channels[channel] = f_id


class Input(Universe):
    def __init__(self,root, u=None):
        self.root = root.find('{%s}Input' % Workspace.xmlns)
        self.plugin = self.root.get('Plugin')
        self.line = self.root.get('Line')


# TODO: this all assumes artnet, make agnostic
class Output(Universe):
    def __init__(self, root, u=None):
        self.root = root.find('{%s}Output' % Workspace.xmlns) 
        self.output_ip = None
        if not self.root and u:
            # generate
            self.root = ET.SubElement(root,"Output")
            self.update(u)
            self.output_ip = u.get('ipaddr')
        else:
            self.parameters = self.root.find('{%s}PluginParameters' % Workspace.xmlns)
            if self.parameters:
                self.output_u = self.parameters.get('outputUni')
                self.output_ip = self.parameters.get('outputIP')
                if 'ArtNet' in self.plugin:
                    self.artnet_ip = self.output_ip
        self.plugin = self.root.get('Plugin')
        self.line = self.root.get('Line')
        
    def update(self, u):
        if u.get('ipaddr') and u.get('artnet_u') != None:
            self.root.set('Plugin', 'ArtNet')
            # TODO: map this by known IP?
            self.root.set('Line', u.get('Line') or "2")
            
            pps = self.root.findall('{%s}PluginParameters' % Workspace.xmlns)
            if len(pps) > 1:
                # delete em all 
                for pp in pps: 
                    self.root.remove(pp)
                pps = []
            if not pps:
                # create one
                print(ET.tostring(self.root))
                print('oops')
                self.parameters = ET.SubElement(self.root, "{%s}PluginParameters" % Workspace.xmlns)
            self.parameters.set('outputIP', u.get('ipaddr'))
            self.parameters.set('outputUni', str(u.get('artnet_u')))


class Fixtures(Engine):
    def __init__(self, root):
        # no Fixtures sub
        self.root = root
        self.items = []
        for item in self.root.findall('{%s}Fixture' % Workspace.xmlns):
            self.items.append(Fixture(item))

        self.names = list(map(lambda x: x.name, self.items))
        self.ids = list(map(lambda x: int(x.id), self.items))
        self._next_id = 0
        for id in self.ids: 
            if int(id) > self._next_id:
                self._next_id = int(id)


    def next_id(self):
        self._next_id += 1
        return self._next_id

        
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
        self.root = root
        self.manufacturer = root.find('{%s}Manufacturer' % Workspace.xmlns).text
        self.model = root.find('{%s}Model' % Workspace.xmlns).text
        self.name = f'{self.manufacturer} - {self.model}'
        self.mode = root.find('{%s}Mode' % Workspace.xmlns).text
        self.id = root.find('{%s}ID' % Workspace.xmlns).text
        self.name = root.find('{%s}Name' % Workspace.xmlns).text
        self.universe = root.find('{%s}Universe' % Workspace.xmlns).text
        self.address = root.find('{%s}Address' % Workspace.xmlns).text
        self.channels = root.find('{%s}Channels' % Workspace.xmlns).text


class FixtureGroups(Engine):
    def __init__(self, root):
        # no FixtureGrops sub 
        self.root = root
        self.items = []
        for item in root.findall('{%s}FixtureGroup' % Workspace.xmlns):
            self.items.append(FixtureGroup(item))

        self.names = list(map(lambda x: x.name, self.items))
        self.ids = list(map(lambda x: x.id, self.items))
        self._next_id = 0
        for id in self.ids:
            if int(id) > self._next_id:
                self._next_id = int(id)

    def add(self, ref):
        self.items.append(FixtureGroup(self.root, ref))

    def delete(self, fg):
        self.items.remove(fg)

    def next_id(self):
        self._next_id += 1
        return self._next_id
            
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
        self.root = root
        self.name = self.root.find('{%s}Name' % Workspace.xmlns).text
        self.id = root.get('ID')
        self.size = Size(root)
        self.heads = Heads(root)

class ChannelsGroup(Engine):
    def __init__(self, root, cg=None):
        self.root = root
        if cg != None:
            self.root.set('ID', cg.get('id'))
            self.root.set('Name', cg.get('name'))
            self.root.set('Value', cg.get('value'))
            self.root.set('InputUniverse', cg.get('InputUniverse'))
            self.root.set('InputChannel', cg.get('InputChannel'))
        self.id = root.get('ID')
        self.name = root.get('Name')
        self.value = root.get('Value')
        self.input_universe = root.get('InputUniverse')
        self.input_channel = root.get('InputChannel')
        self.mapping = root.text
   
    def update(self, cg):
        for k,v in data.items():
            self.root.set(k,v)
    

class Size(FixtureGroup):
    def __init__(self, root, fg=None):
        self.root = root
        self.root = root.find('{%s}Size' % Workspace.xmlns)
        self.x = self.root.get('X')
        self.y = self.root.get('Y')


class Heads(FixtureGroup):
    def __init__(self, root, fg=None):
        self.root = root
        self.items = []
        if fg != None:
            for head in fg.get('heads'):
                self.items.append(Head(root, head))
        else: 
            for item in root.findall('{%s}Head' % Workspace.xmlns):
                self.items.append(Head(item))

    def update(self, heads):
        for head in heads:
            e_head = heads.find_by_id(head.get('id'))
            if e_head:
                e_head.update(head)
            else:
                self.items.append(Head(self.root, head))
        

class Head(Heads):
    def __init__(self, root, head=None):
        self.root = root
        if head != None:
            self.root.set('X', head.get('X'))
            self.root.set('Y', head.get('Y'))
            self.root.text = head.get('id')
            self.root.set('Fixture', head.get('Fixture'))
        self.x = root.get('X')
        self.y = root.get('Y')
        self.id = root.text
        self.fixture = root.get('Fixture')
        self.fixture_id = root.get('Fixture')

    def update(self, head):
        for k,v in data.items():
            self.root.set(k,v)

class Functions(Engine):
    def __init__(self, root):
        # no Functions sub group
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
        if fixture:
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
        self.modes = Modes(self.root, self.channels)
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
    def __init__(self, root, channels):
        self.items = []
        for item in root.findall('{%s}Mode' % FixtureDefinition.xmlns):
            self.items.append(Mode(item, channels))

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
    def __init__(self, root, channels):
        self.root = root
        self.name = root.get('Name')
        self.mode_channels = ModeChannels(root, channels)
        self.channels = self.mode_channels.channels
        self.heads = ModeHeads(root, self.mode_channels)

class ModeChannels(Mode):
    def __init__(self, root, channels):
        self.root = root
        self.items = []
        self.channels = []
        for item in root.findall('{%s}Channel' % FixtureDefinition.xmlns):
            mc = ModeChannel(item, channels)
            self.items.append(mc)
            self.channels.append(mc.channel)
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
    def __init__(self, root, channels):
        self.root = root
        self.name = root.text
        self.number = root.get('Number')
        self.channel = channels.find_by_name(self.name)

class ModeHeads(Mode):

    def __init__(self, root, mode_channels):
        self.root = root
        self.items = []
        self.count = 0
        for item in root.findall('{%s}Head' % FixtureDefinition.xmlns):
            self.count += 1
            mh = ModeHead(item, mode_channels, self.count)
            self.items.append(mh)

    def find_by_id(self, id):
        return self.items[int(id)]
    
class ModeHead(Mode):
    def __init__(self, root, mode_channels, count):
        self.root = root
        self.id = count
        self.mode_channels = ModeHeadChannels(root, mode_channels)

class ModeHeadChannels(ModeHead):
    def __init__(self, root, mode_channels):
        self.root = root
        self.items = []
        for hc in root.findall('{%s}Channel' % FixtureDefinition.xmlns):
            self.items.append(ModeHeadChannel(hc, mode_channels))
        self.names = list(map(lambda x: x.channel.name, self.items))

class ModeHeadChannel(ModeHeadChannels):
    def __init__(self, root, mode_channels):
        self.root = root
        self.number = self.root.text
        self.mode_channel = mode_channels.find_by_number(self.number)
        self.channel = self.mode_channel.channel
    