# qlcplus-tools
Tools for managing QLC+ Files

This repo is a collection of tools I used to manage QLC showfiles.  I will work to 
add functionality as I go.  Much of this is predicated on my use case.. which is:

- configure fixtures
- create fixture groups based on show design
- create scenes by fixture features 
- create RGBMatrix and EFX as needed
- combine scenes, matrix, EFX  in collections as cue points 
- assemble collections into chaser by points in the show
- cue the show 

This way .. chaging a head value doesn't require touching the scene values .. just changing the scene in the collection from one feature to another.  This has some caveats:

- Most of my scenes are Lights ON or OFF or fading up or down .. not much level stuff because of the show ( we're on a prelit stage and using lighting mostly for effect )
- Can't really "live edit" the show .. have to reprogram in the collection. 

## expand_fixture_features
 
This tool will create scenes for fixture attributes that match across a fixture group. 

- COLORS - for each major color in a color wheel ( or for the colors on the wheel it has ) there will be a scene created with that color set on RGB(W) or the wheel, and the Intensity 
to full. 

- Other - for each named "Capability" within that channel function, a scene is created to enable that specific function. 


## sync_mitti 
I use the Mitti Video tool to display basic video on screens as part of our show.  Given the number of potential cues in Mitti that must match up to the cues in QLC; I wanted a 
way to syncronise these two so when a 'cue' is placed in QLC for a collection, it will be 
consistently activated on Mitti when the cue is activated on QLC. 

So it creates global and cue functions that do not require values, each as Script entries using the sendosc command. 