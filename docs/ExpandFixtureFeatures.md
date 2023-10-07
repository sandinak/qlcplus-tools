# Expand Fixture Features

The tool ingests a showfile and configuration; and then writes a new showfile ( or in place ) with the configuration data expanded into scene folders based on the fixture groups defined.  It's designed to be fixture agnostic, so you can mix "color wheel" heads and "RGB(W)" heads in your Fixture Groups and still get a color scene for that group that works for both sets. 

## Usage

1. setup your show file as per [this document](Showfile_Design.md) with Fixture Groups that would be used in scenes in the show
1. setup this tool and make sure it's ready to operate using the help
    ```
    git clone git@github.com:sandinak/qlcplus-tools.git
    make 
    . sourceme
    ./bin/expand_fixture_features.py --help
    ``` 
1. Run the tool against your file to generate the scenes 
    ```
    ./bin/expand_fixture_features.py -d -v -o newfile.qxw showfile.qxw
    ```
1. run QLC+ on the file and review the new scenes.

## Advanced

- if you want other colors/intensities than the defaults.. you can edit the QLC.py file to add/extend the color pallet.  I am considering making this an external config file if there's interest
- once you're comfortable using the tool, you can just edit the showfile in place.  The tool is designed to be NON-Destructive against existing config in the file; and only add new config if needed ( eg .. it's idempotent ) 


