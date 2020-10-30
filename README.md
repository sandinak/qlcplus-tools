# qlcplus-tools

Tools for managing QLC+ Files

This repo is a collection of tools I used to manage QLC showfiles.  I will work to 
add functionality as I go.  Much of this is predicated on my use case.. which is:

- configure fixtures and other DMX targets
- create fixture groups based on show design
- create scenes by fixture features (tedious for every base combination)
- create RGBMatrix and EFX as needed
- combine scenes, matrix, EFX in collections as cue points 
- assemble collections into chaser by points in the show with timing and fading
- cue the show 

This way .. chaging a head value doesn't require touching the scene values .. just changing the scene in the collection from one feature to another.  This has some caveats:

- Most of my scenes are Lights ON or OFF or fading up or down .. not much level stuff because of the show ( we're on a prelit stage and using lighting mostly for effect )
- Can't really "live edit" the DMX Values in the scenes show .. have to reprogram in the collection.  However, changing the view of a scene in the show is now just changing the 
QLCScenes in the collection.  

## Naming Conventions
This is predicated on what's been easy for me to teach to students and easy to find when 
assembling scenes into collections for a show

### Scenes
- Colors are in their own folder by Fixture Group and will include all colors that can be supported by ALL fixtures in that group ( so RGB fixtures are constrained if there's a color wheel. )
- Positions are in their own folder by FixtureGroup and right now just a base mid position is created to be cloned into other positions. 
- Capabilities are in a FixtureGroups folder and broken out by the name given in the 
fixture definition and the name given the capability.  All are set by the minimum Val.

# Getting Started
This tooling is setup to run in a venv locally and cleanly, to get things setup 

```
. sourceme
make
```
You can then run the python scripts in bin: 

- All the programs have a --help option 
- All the programs are non-destructive .. they should not touch any existing configuration

# Programs

## expand_fixture_features
 
This tool will create scenes for fixture attributes that match across a fixture group. 

- COLORS - for each major color in a color wheel ( or for the colors on the wheel it has ) there will be a scene created with that color set on RGB(W) or the wheel, and the Intensity 
to full. 

- POSITION - for moving heads, will setup a 'base' position which is midway on H and V.  This is useful to clone and minimize movement.

- Other - for each named "Capability" within that channel function, a scene is created to enable that specific function. 


## sync_mitti 
I use the Mitti Video tool to display basic video on screens as part of our show.  Given the number of potential cues in Mitti that must match up to the cues in QLC; I wanted a 
way to syncronise these two so when a 'cue' is placed in QLC for a collection, it will be 
consistently activated on Mitti when the cue is activated on QLC. 

So it creates global and cue functions that do not require values, each as Script entries using the sendosc command. 