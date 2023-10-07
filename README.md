# qlcplus-tools

Tools for managing and expanding QLC+ Files

This repo is a collection of tools I use to manage QLC showfiles.  I will work to 
add functionality as I go.  Much of this is predicated on my use case.. which is:

1. configure fixtures and other DMX targets for the stage
1. create fixture groups based on show design
1. create sets of scenes by fixture features (tedious for every base combination)
1. create RGBMatrix and EFX as needed
1. combine scenes, matrix, EFX in collections as cue points 
1. assemble collections into chaser by points in the show with timing and fading
1. cue the show 

You can see more details in [ShowfileDesign.md](docs/ShowfileDesign.md)

## Naming Conventions
This is predicated on what's been easy for me to teach to students and easy to find when assembling scenes into collections for a show

- each FixtureBasedScene Name uses the full path in the storage structure to allow clean identification of the scene
- each Collection is named based on thier use case
    - for cuepoints in the show I use {song}-{section}.{cue}-{name} to allow easy identification


# Getting Started

This tooling is setup to run in a venv locally and cleanly, to get things setup

```
git clone git@github.com:sandinak/qlcplus-tools.git
. sourceme
make
```

- All the programs have a --help option 
- All the programs are designed to be non-destructive .. they should not touch any existing configuration

## How to use these tools:

1. Create a new show file with fixtures mapped to universes as usual
2. Create FixtureGroups of lights you'd like to address simultaniously, these can be of the same fixture type or different types
3. Save the file
4. Run the programs against the file. There is an --output option, however the programs are designed to be non-destructive and will only create things.
5. Read the file back into QLC+
6. Profit!

## NOTES

- So you can run these programs as many times as you'd like .. they're idempotent
- If you add/change/update FixtureGroups .. you can just re-run the programs on the files.
- As noted .. these are non-destructive.. so if you remove FixtureGroups .. this will NOT remove the corresponding scenes for those Groups

# Programs

## expand_fixture_features

This tool has two major functions

- [Expand Fixture Features](./docs/ExpandFixtureFeatures.md) - generate scenes for fixture features.
- [Expand RGB Matrix Layouts](./docs/ExpandRGBLayouts.md) - export/import .xls files with layouts 

## sync_mitti 
I use the Mitti Video tool to display basic video on screens as part of our show.  Given the number of potential cues in Mitti that must match up to the cues in QLC; I wanted a way to syncronise these two so when a 'cue' is placed in QLC for a collection, it will be consistently activated on Mitti when the cue is activated on QLC. 

So it creates global and cue functions that do not require values, each as Script entries using the sendosc command. 

## generate_fixtures

This was a one-off program that generates large sets of fixtures.  It's mostly deprecated and here as a framework if needed again.

