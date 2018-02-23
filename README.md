This repository puts together:

```
(1)
screen_tracker_offline.py
```

a plugin for Pupil Player (tested with Pupil Player Version 1.4.1) that permits
the expression of coordinates in relation to the four corners of the computer
screen
   
```
(2)
check_gaze_drift.r
get_button_rate.r
get_gaze_rates.r
util_correct.r
util_obtain.r
```

five R scripts for gaze-coordinates correction and analysis (the first three are
data-analysis scripts, the last two are script utilities called by the former;
util_correct.r contains source code for cloud-center correction)

```
(3)
p1
├── p1_1
│   ├── events.dat
│   └── gaze.dat
├── p1_2
│   ├── events.dat
│   └── gaze.dat
└── p1_3
    ├── events.dat
    └── gaze.dat
...
```

a tree of data files that can be analyzed through these R scripts.

==========
How to use the plugin:

Before anything else, copy the screen_tracker_offline.py file to your
`pupil_player_settings/plugins/` folder (this folder is created by Pupil and you
should find it in your `HOME` or `USER` directory).

Then launch Pupil Player with the recording session you are interested in and
follow these steps:

a. Click on the 'Plugin Manager' icon on the right of the screen. The name of
the plugin ("Screen Tracker Offline") should appear in the plugin list. Click on
the corresponding circular icon (right of the name).

b. The plugin will open a small menu window. Click on the "Update Cache" button. The
plugin will scan all the video frames in your session to detect the corners of
the computer screen whenever present. Be patient, this may take a few minutes.
The screen will become shaded and freeze during detection. Once the detection is
over, the screen will brighten again, and you will be able to see the result of
the detection in the form of a blue trapezoid being superimposed on each frame
with the screen borders detected.

c. Click on the "Add screen surface" button. This step is required to include the
detected surface (in this case, the computer screen with its four corners) into
the data. This surface will appear as "Surface 0" with an arbitrary name, width,
and height. The width and height provided by default are 1 and 1, corresponding
to normalized 0-1 Cartesian coordinates for the screen surface. (However, you
are free to change these values for other ones, such as the width and height of
your computer monitor in pixels, for example.)

d. Finally, click on the Pupil button for exporting the data. (This is a
circular button on the left side of the screen with a download-like arrow.) The
data with the transformed coordinates will be saved in your session folder, in a
new subfolder created by Pupil and named after the time interval of the session
just processed.