#! /usr/bin/env python

'''
============================================================================
Title: manage qlc showfile
Description:
QLC Libraries
============================================================================
'''

import logging as log
import xml.etree.ElementTree as ET
from xml.dom import minidom
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
rgbw = {        #shortname           R    G    B    W
    'Red':      { 'n':'R',    'rgbw': [255,   0,   0,   0], },
    'Green':    { 'n':'G',    'rgbw': [0,   255,   0,   0], },
    'Blue':     { 'n':'B',    'rgbw': [0,     0, 255,   0], },
    'Yellow':   { 'n':'Y',    'rgbw': [255, 255,   0,   0], },
    'Cyan':     { 'n':'C',    'rgbw': [0,   255, 255,   0], },
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
    'Red/W':    { 'n':'RW',   'rgbw': [255,   0,   0, 255], },
    'Green/W':  { 'n':'GW',   'rgbw': [0,   255,   0, 255], },
    'Blue/W':   { 'n':'BW',   'rgbw': [0,     0, 255, 255], },
    'Yellow/W': { 'n':'YW',   'rgbw': [255, 255,   0, 255], },
    'Cyan/W':   { 'n':'CW',   'rgbw': [0,   255, 255, 255], },
    'Red/W':    { 'n':'MW',   'rgbw': [255,   0, 255, 255], },
    'Purple/W': { 'n':'PW',   'rgbw': [128,   0, 255, 255], },
    'Rasp/W':   { 'n':'RaW',  'rgbw': [255,   0, 128, 255], },
    'Orange':   { 'n':'OrW',  'rgbw': [255, 128,   0, 255], },
    'Ocean':    { 'n':'OcW',  'rgbw': [  0, 128, 128, 255], },
    'Turqoise': { 'n':'TW',   'rgbw': [  0, 255, 128, 255], },
    'Purple':   { 'n':'PW',   'rgbw': [128,   0, 255, 255], },
    'Pink':     { 'n':'PkW',  'rgbw': [255,   0, 128, 255], },
}

SPOT_ON_CHANNELS = [
    'Master Dimmer',
    'Strobe/Shutter',
    'Shutter',
    'Dimmer',
    'Itensity',
    'Shutter',
]

Movement_Channel_Names = [
    'Pan',
    'Level',
    'Horizontal',
    'Tilt',
    'Vertical'
]

blank = '''
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
XMLNS = 'http://www.qlcplus.org/Workspace'
DOCTYPE='''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Workspace>
'''.strip()


def _strip(elem):
    for elem in elem.iter():
        if(elem.text):
            elem.text = elem.text.strip()
        if(elem.tail):
            elem.tail = elem.tail.strip()


class qlc:

    def __init__(self, **kwargs):
        ''' setup class '''
        # expand common targets
        self.__dict__.update(kwargs)

        ET.register_namespace('', XMLNS)

        if self.file:
            self.tree = ET.parse(self.file)
            self.root = self.tree.getroot()
        else:
            self.root = ET.fromstring(blank)

        self.fixture_definitions = {}
        self.load_fixtures(FIXTURE_PATHS)

        # extract useful objects
        self.creator = self.root.find('{%s}Creator' % XMLNS)
        self.engine = self.root.find('{%s}Engine' % XMLNS)
        self.iomap = self.engine.find('{%s}InputOutputMap' % XMLNS)
        self.universes = self.iomap.findall('{%s}Universe' % XMLNS)

        self.fixtures = self.engine.findall('{%s}Fixture' % XMLNS)
        self.fixture_groups = self.engine.findall('{%s}FixtureGroup' % XMLNS)
        self.fg_id_by_name = {}

        self.text = None

        # cache these
        self.last_function_id = 0
        self.functions = self.engine.findall('{%s}Function' % XMLNS)
        for f in self.functions:
            _id = f.attrib.get('ID')
            if int(_id) > self.last_function_id:
                self.last_function_id = int(_id)

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
                self.read_fixture(t_path)
    
    def read_fixture(self,path):
        xmlns = 'http://www.qlcplus.org/FixtureDefinition'
        # read/parse the file
        try: 
            tree = ET.parse(path)
        except Exception as e:
            return
        fixture = tree.getroot()
        f = {}
        f['manufacturer'] = fixture.find('{%s}Manufacturer' % xmlns).text
        f['model'] = fixture.find('{%s}Model' % xmlns).text
        f['type'] = fixture.find('{%s}Type' % xmlns).text

        # skip pixels .. we're not dealing with those
        if 'Bar' in f['type'] or 'Pixel' in f['type']:
            return

        # get the modes, we'll need these for the colors
        f['modes'] = {}
        f['groups'] = {}
        f_modes = fixture.findall('{%s}Mode' % xmlns)
        for f_mode in f_modes:
            name = f_mode.get('Name')
            #print('mode name %s' % name)
            fmc = {}
            mode_channels = f_mode.findall('{%s}Channel' % xmlns)
            for mc in mode_channels:
                attr = mc.text
                cid = int(mc.get('Number'))
                fmc[cid] = attr
            f['modes'][name] = fmc

        # if no mode, create a default mode
        if len(f['modes']) == 0:
            f['modes']['Default'] = {}

        # if we need colors for a spot .. lets see if they're
        # defined, also if not a mode, we generate one using the
        # existing channels
        f_channels = fixture.findall('{%s}Channel' % xmlns)
        dfmc = {}
        cid = 0
        for fc in f_channels:
            fc_name = fc.get('Name')
            fc_group_entry = fc.find('{%s}Group' % xmlns)
            if fc_group_entry == None:
                continue

            # add channel to the groups list
            fc_group = fc_group_entry.text
            f['groups'][fc_name] = fc_group

            # add to default mode if it exists
            if 'Default' in f['modes']: 
                name = fc.get('Name')
                f['modes']['Default'][name] = id
                cid += 1

            # add color capabilities ... .EU spelling
            if fc_group == 'Colour':
                f[fc_name] = {}
                color_capabilities = fc.findall('{%s}Capability' % xmlns)
                for cc in color_capabilities:
                    name = cc.text
                    val = str(int(cc.get('Min')) + 1)
                    f[fc_name][name] = val

            # add other capabilities by group
            elif 'Gobo' in fc_group:
                f[fc_name] = {}
                capabilities = fc.findall('{%s}Capability' % xmlns)
                for c in capabilities:
                    name = c.text
                    val = str(int(c.get('Min')))
                    f[fc_name][name] = val

            # add capabilties by name
            elif 'Auto Focus' in fc_name or 'Prism' in fc_name:
                f[fc_name] = {}
                capabilities = fc.findall('{%s}Capability' % xmlns)
                for c in capabilities:
                    name = c.text
                    val = str(int(c.get('Min')))
                    f[fc_name][name] = val
                    

        # apply
        # print('Creating: %s, %s' % (f['manufacturer'],f['model']))
        if not f['manufacturer'] in self.fixture_definitions:
            self.fixture_definitions[f['manufacturer']] = {}
        self.fixture_definitions[f['manufacturer']][f['model']] = f
    
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

    def write(self):
        self.text = self._gen_text()
        f = open(self.file, 'w')
        f.write(self.text)
        f.close()

    def universe(self, **kwargs):
        last_u_id = 0
        this_u = None
        for u in self.universes:
            _id = int(u.get('ID'))
            print("_id: %d , id: %d" % (_id, kwargs.get('ID')))
            if _id == kwargs.get('ID'):
                this_u = u
            if _id > last_u_id:
                last_u_id = _id

        # create a new U if needed
        if this_u == None:
            this_u = ET.SubElement(self.iomap, 'Universe')
            last_u_id += 1
            this_u.set('ID', str(last_u_id))

        # set the name to match
        this_u.set('Name', kwargs.get('Name'))

        # update it if we have new data
        if Input := kwargs.get('Input'):
            i = this_u.find('{%s}Input' % XMLNS)
            if not i:
                i = ET.SubElement(this_u, 'Input')
            for k, v in Input.items():
                i.set(k, v)

        if InputParams := kwargs.get('InputParams'):
            ip = i.find('{%s}PluginParameters' % XMLNS)
            if not ip:
                ip = ET.SubElement(i, 'PluginParameters')
            for k, v in InputParams.items():
                ip.set(k, v)

        if Output := kwargs.get('Output'):
            o = this_u.find('{%s}Input' % XMLNS)
            if not o:
                o = ET.SubElement(this_u, 'Input')
            for k, v in Output.items():
                o.set(k, v)

        if OutputParams := kwargs.get('OutputParams'):
            op = o.find('{%s}PluginParameters' % XMLNS)
            if not op:
                op = ET.SubElement(o, 'PluginParameters')
            for k, v in OutputParams.items():
                op.set(k, v)

    def fattr_speed(self,f,**kwargs):
        default_speed = {
            'FadeIn': '0',
            'FadeOout': '0',
            'Duration': '0'
        } 
        if speed := kwargs.get('Speed') or default_speed:
            s = f.find('{%s}Speed' % XMLNS)
            if s == None:
                s = ET.SubElement(f, 'Speed')
            for k, v in speed.items():
                s.set(k, v)

    def function(self, **kwargs):
        Name = kwargs.get('Name')
        ID = kwargs.get('ID')
        Type = kwargs.get('Type')
        Path = kwargs.get('Path')

        # go find if we can, ID is most significant
        this_func = None
        if Name and Type:
            for f in self.functions:
                if ID == f.attrib.get('ID'):
                    this_func = f
                elif Name == f.attrib.get('Name'):
                    this_func = f

        # if we dont' find it .. create it
        if not this_func:
            this_func = ET.SubElement(self.engine, 'Function')
             # select next id 
            if not ID:
                self.last_function_id +=1
                ID = self.last_function_id
            this_func.set('ID', str(ID))

        # set primatives
        this_func.set('Name', Name)
        this_func.set('Type', Type)
        if Path:
           this_func.set('Path', Path)

        if Type == 'Script':
            self.f_script(this_func, **kwargs)
        elif Type == 'Scene': 
            self.f_scene(this_func, **kwargs)

    def f_script(self, f, **kwargs):
        
        self.fattr_speed(f, **kwargs)

        default_direction = 'Forward'
        if direction := kwargs.get('Direction') or default_direction:
            d = f.find('{%s}Direction' % XMLNS)
            if d == None:
                d = ET.SubElement(f, 'Direction')
            d.text = direction

        default_runorder = 'Loop'
        if runorder := kwargs.get('RunOrder') or default_runorder:
            r = f.find('{%s}RunOrder' % XMLNS)
            if r == None:
                r = ET.SubElement(f, 'RunOrder')
            r.text = runorder

        if kwargs.get('Command'):
            c = f.find('{%s}Command' % XMLNS)
            if c == None:
                c = ET.SubElement(f, 'Command')
            command = urllib.parse.quote(kwargs.get('Command'), safe='')
            c.text = command

    # create a scene
    def f_scene(self, f, **kwargs):
        fvals = kwargs.get('FixtureVals')
        self.fattr_speed(f, **kwargs)

        # set fixture vals
        fvs = f.findall('{%s}FixtureVal' % XMLNS)
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

   
    def fixture_group_names(self):
        r = []
        for fg in self.fixture_groups:
            name = fg.find('{%s}Name').text 
            r.append(name)
            self.fg_id_by_name[name] = fg.get('ID')
        return r
    
    def expand_fixture_group_capabilities(self):
        for fg in self.fixture_groups:
            # get fixture id from the first head
            fg_name = fg.find('{%s}Name' % XMLNS).text
            heads = fg.findall('{%s}Head' % XMLNS)
            if len(heads) == 0 :
                continue
            rfid = heads[0].get('Fixture')
            
            # now find the fixture
            for f in self.fixtures:
                if f.find('{%s}ID' % XMLNS).text == rfid:
                    rf = f
                    break
            
            # get fixture color capabiltiies, first head works
            rf_manufacturer = rf.find('{%s}Manufacturer' % XMLNS).text
            rf_model = rf.find('{%s}Model' % XMLNS).text
            rf_mode = rf.find('{%s}Mode' % XMLNS).text
            if rf_mode == None:
                rf_mode = 'Default'

            # get the dict of fixture channels
            fchannels = self.fixture_definitions[rf_manufacturer][rf_model]['modes'][rf_mode]

            # get a list of fixture_channel_groups
            fc_groups = self.fixture_definitions[rf_manufacturer][rf_model]['groups']

            print('name: %s == %s' % (fg_name, fchannels) )
            for cid,fc in fchannels.items():
                print('channel: %s groups: %s' % (fc, fc_groups))
                if fc in fc_groups: 
                    fc_group = fc_groups[fc]
                if 'Gobo' in fc or 'Auto Focus' in fc or 'Prism' in fc:
                    fvals = {}
                    for cname, cval in self.fixture_definitions[rf_manufacturer][rf_model][fc].items():
                        # skip rotation 
                        if 'Rotate' in cname: 
                            continue
                        for head in heads: 
                            hfid = head.get('Fixture')
                            cid = 0
                            cstr_l = []
                            for cid,c in sorted(fchannels.items()):
                                fval = None
                                if fc == c:
                                    fval = '%d,%d' % (cid, int(cval))
                                cid += 1
                                if fval: 
                                    cstr_l.append(fval)
                            fval = "," . join(cstr_l)
                            fvals[hfid] = fval
                        self.function(
                            Type = 'Scene',
                            Path = 'Fixtures/%s/%s' % ( fg_name, fc ),
                            Name = 'Fixtures/%s/%s/%s' % ( fg_name, fc, cname ),
                            FixtureVals = fvals,
                        )

                if 'Colo' in fc:
                    fvals = {}
                    for cname, cval in self.fixture_definitions[rf_manufacturer][rf_model][fc].items():
                        # skip rotation 
                        if 'Rotate' in cname: 
                            continue
                        for head in heads: 
                            hfid = head.get('Fixture')
                            cid = 0
                            cstr_l = []
                            for cid,c in sorted(fchannels.items()):
                                fval = None
                                if c in SPOT_ON_CHANNELS:
                                    fval = '%d,255' % cid 
                                elif c == 'Color':
                                    fval = '%d,%d' % (cid, int(cval))
                                cid += 1
                                if fval: 
                                    cstr_l.append(fval)
                            fval = "," . join(cstr_l)
                            fvals[hfid] = fval
                        self.function(
                            Type = 'Scene',
                            Path = 'Fixtures/%s/Colors' % ( fg_name ),
                            Name = 'Fixtures/%s/Colors/%s' % ( fg_name, cname ),
                            FixtureVals = fvals,
                        )

                if 'Red' in fc:
                    # generate generic colors
                    for cname,cd in rgbw.items(): 
                        fvals = {}
                        for head in heads: 
                            hfid = head.get('Fixture')
                            cid = 0
                            cstr_l = []
                            for cid,c in sorted(fchannels.items()):
                                fval = None
                                if c == 'Intensity' or c == 'Dimmer':
                                    fval = '%d,255' % cid 
                                elif c == 'Red':
                                    fval = '%d,%d' % (cid, cd['rgbw'][0])
                                elif c == 'Green':
                                    fval = '%d,%d' % (cid, cd['rgbw'][1])
                                elif c == 'Blue':
                                    fval = '%d,%d' % (cid, cd['rgbw'][2])
                                elif c == 'White':
                                    fval = '%d,%d' % (cid, cd['rgbw'][3])
                                cid += 1
                                if fval: 
                                    cstr_l.append(fval)
                            fval = "," . join(cstr_l)
                            fvals[hfid] = fval

                        self.function(
                            Type = 'Scene',
                            Path = 'Fixtures/%s/Colors' % ( fg_name ),
                            Name = 'Fixtures/%s/Colors/%s' % ( fg_name, cname ),
                            FixtureVals = fvals,
                        )

                # generate generic position
                if ('Pan' in fc_group or 'Pan' in fc) and not 'Speed' in fc:
                    fvals = {}
                    for head in heads: 
                        hfid = head.get('Fixture')
                        cid = 0
                        cstr_l = []
                        for cid,c in sorted(fchannels.items()):
                            fval = None
                            for cn in Movement_Channel_Names:
                                if cn in c and not 'Speed' in c:
                                    fval = '%d,128' % cid 
                            cid += 1
                            if fval: 
                                cstr_l.append(fval)
                        fval = "," . join(cstr_l)
                        fvals[hfid] = fval

                    self.function(
                        Type = 'Scene',
                        Path = 'Fixtures/%s/Positions' % ( fg_name ),
                        Name = 'Fixtures/%s/Positions/Preset' % ( fg_name ),
                        FixtureVals = fvals,
                    )                    





