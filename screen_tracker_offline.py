# -*- coding: utf-8 -*-
'''
  Pupil Player Third Party Plugins by cpicanco
  Copyright (C) 2016 Rafael Picanço.

  The present file is distributed under the terms of the GNU General Public License (GPL v3.0).

  You should have received a copy of the GNU General Public License
  along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

# python
import sys, os
from pathlib import Path

# third party
import cv2
import numpy as np
from glfw import glfwGetCurrentContext, glfwGetCursorPos, glfwGetWindowSize

# pupil
from file_methods import Persistent_Dict, save_object
from pyglui import ui
from pyglui.cygl.utils import *
from methods import normalize

from offline_surface_tracker import Offline_Surface_Tracker
from offline_reference_surface import Offline_Reference_Surface
from surface_tracker import Surface_Tracker
from square_marker_detect import draw_markers,m_marker_to_screen
from reference_surface import Reference_Surface

#logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def sortCorners(corners, center):
    """
    corners : list of points 
    center : point
    """
    top = []
    bot = []

    for corner in corners:
        if corner[1] < center[1]:
            top.append(corner)
        else:
            bot.append(corner)

    corners = np.zeros(shape=(4,2))

    if (len(top) == 2) and (len(bot) == 2):
        # top left
        if top[0][0] > top[1][0]:
            tl = top[1]
        else:
            tl = top[0]

        # top right
        if top[0][0] > top[1][0]:
            tr = top[0]
        else:
            tr = top[1]

        # botton left
        if bot[0][0] > bot[1][0]:
            bl = bot[1]
        else:
            bl = bot[0]

        # botton right
        if bot[0][0] > bot[1][0]:
            br = bot[0]
        else:
            br = bot[1]       

    try:
        corners[0] = np.array(tl)
        corners[1] = np.array(tr)
        corners[2] = np.array(br)
        corners[3] = np.array(bl)
    except Exception as e:
        # print(center,'\n')
        # print(top,'\n')
        # print(bot,'\n')
        pass

    return corners

def detect_screens(gray_img, draw_contours=False):
    edges = cv2.adaptiveThreshold(gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, -5)

    _, contours, hierarchy = cv2.findContours(edges,
                                    mode=cv2.RETR_TREE,
                                    method=cv2.CHAIN_APPROX_SIMPLE,offset=(0,0)) #TC89_KCOS
    
    if draw_contours:
        cv2.drawContours(gray_img, contours,-1, (0,0,0))
    
    # remove extra encapsulation
    hierarchy = hierarchy[0]
    contours = np.array(contours)

    # keep only contours                        with parents     and      children
    contours = contours[np.logical_and(hierarchy[:,3]>=0, hierarchy[:,2]>=0)]

    contours = np.array(contours)
    screens = []
    if contours is not None: 
        # keep only > thresh_area   
        contours = [c for c in contours if cv2.contourArea(c) > (20 * 2500)]
        
        if len(contours) > 0: 
            # epsilon is a precision parameter, here we use 10% of the arc
            epsilon = cv2.arcLength(contours[0], True)*0.1

            # find the volatile vertices of the contour
            aprox_contours = [cv2.approxPolyDP(contours[0], epsilon, True)]

            # we want all contours to be counter clockwise oriented, we use convex hull for this:
            # aprox_contours = [cv2.convexHull(c,clockwise=True) for c in aprox_contours if c.shape[0]==4]

            # we are looking for a convex quadrangle.
            rect_cand = [r for r in aprox_contours if r.shape[0]==4]

            # if draw_contours:
            #     cv2.drawContours(gray_img, rect_cand,-1, (0,0,0))

            # screens
            for r in rect_cand:
                r = np.float32(r)

                # define the criteria to stop and refine the screen verts
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
                cv2.cornerSubPix(gray_img,r,(3,3),(-1,-1),criteria)

                corners = np.array([r[0][0], r[1][0], r[2][0], r[3][0]])

                # we need the centroid of the screen
                # M = cv2.moments(corners.reshape(-1,1,2))
                # centroid = np.array([M['m10']/M['m00'], M['m01']/M['m00']])
                # print 'a', centroid

                centroid = corners.sum(axis=0, dtype='float64')*0.25
                centroid.shape = (2)
                # print 'b', centroid

                # do not force dtype, use system default instead
                # centroid = [0, 0]
                # for i in corners:
                #     centroid += i
                # centroid *= (1. / len(corners))
                # print 'c', centroid

                corners = sortCorners(corners, centroid)
                r[0][0], r[1][0], r[2][0], r[3][0] = corners[0], corners[1], corners[2], corners[3]

                # r_norm = r/np.float32((gray_img.shape[1],gray_img.shape[0]))
                # r_norm[:,:,1] = 1-r_norm[:,:,1]
                
                screen = {'id':32,'verts':r.tolist(),'perimeter':cv2.arcLength(r,closed=True),'centroid':centroid.tolist(),"frames_since_true_detection":0,"id_confidence":1.}
                screens.append(screen)

    return screens

class Global_Container(object):
    pass  

# modified version of marker_detector
class Screen_Tracker(Surface_Tracker):
    """docstring
    """
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        for p in self.g_pool.plugins:
            if p.class_name == 'Marker_Detector':
                p.alive = False
                break

    def init_gui(self):
        if self.g_pool.app == "player":
            self.alive = False
            logger.error('For capture only.')
            return
        self.menu = ui.Growing_Menu('Screen Tracker')
        self.g_pool.sidebar.append(self.menu)

        self.button = ui.Thumb('running',self,label='T',hotkey='t')
        self.button.on_color[:] = (.1,.2,1.,.8)
        self.g_pool.quickbar.append(self.button)
        self.add_button = ui.Thumb('add_surface',setter=self.add_surface,getter=lambda:False,label='A',hotkey='a')
        self.g_pool.quickbar.append(self.add_button)
        self.update_gui_markers()

    def update_gui_markers(self):

        def close():
            self.alive = False

        self.menu.elements[:] = []
        self.menu.append(ui.Button('Close',close))
        self.menu.append(ui.Info_Text('This plugin detects the outmost screen visible in the scene. Ideal screen is white rect in a black backgroud. You can define a surface using 1 visible screen within the world view by clicking *add surface*.'))
        self.menu.append(ui.Switch('robust_detection',self,label='Robust detection'))
        self.menu.append(ui.Slider('min_marker_perimeter',self,step=1,min=10,max=500))
        self.menu.append(ui.Switch('locate_3d',self,label='3D localization'))
        self.menu.append(ui.Selector('mode',self,label="Mode",selection=['Show Markers and Surfaces','Show marker IDs'] ))
        self.menu.append(ui.Button("Add surface", lambda:self.add_surface('_'),))

        for s in self.surfaces:
            idx = self.surfaces.index(s)
            s_menu = ui.Growing_Menu("Surface %s"%idx)
            s_menu.collapsed=True
            s_menu.append(ui.Text_Input('name',s))
            s_menu.append(ui.Text_Input('x',s.real_world_size,label='X size'))
            s_menu.append(ui.Text_Input('y',s.real_world_size,label='Y size'))
            s_menu.append(ui.Button('Open Debug Window',s.open_close_window))
            #closure to encapsulate idx
            def make_remove_s(i):
                return lambda: self.remove_surface(i)
            remove_s = make_remove_s(idx)
            s_menu.append(ui.Button('remove',remove_s))
            self.menu.append(s_menu)

    def recent_events(self,events):
        if 'frame' in events:
            frame = events['frame']
            self.img_shape = frame.height,frame.width,3

            if self.running:
                gray = frame.gray

                # hack "self.markers" instead "self.screens" is keeped for inheritence compatibility
                self.markers = detect_screens(gray)

                if self.mode == "Show marker IDs":
                    draw_markers(frame.img,self.markers)
                    events['frame'] = frame

            # locate surfaces, map gaze
            for s in self.surfaces:
                s.locate(self.markers,self.camera_calibration,self.min_marker_perimeter,self.min_id_confidence, self.locate_3d)
                if s.detected:
                    s.gaze_on_srf = s.map_data_to_surface(events.get('gaze_positions',[]),s.m_from_screen)
                else:
                    s.gaze_on_srf =[]

            events['surface'] = []
            for s in self.surfaces:
                if s.detected:
                    events['surface'].append({
                        'name':s.name,
                        'uid':s.uid,
                        'm_to_screen':s.m_to_screen.tolist(),
                        'm_from_screen':s.m_from_screen.tolist(),
                        'gaze_on_srf': s.gaze_on_srf,
                        'timestamp':frame.timestamp,
                        'camera_pose_3d':s.camera_pose_3d.tolist() if s.camera_pose_3d is not None else None
                    })

            if self.running:
                self.button.status_text = '{}/{}'.format(len([s for s in self.surfaces if s.detected]), len(self.surfaces))
            else:
                self.button.status_text = 'tracking paused'

            if self.mode == 'Show Markers and Surfaces':
                # edit surfaces by user
                if self.edit_surf_verts:
                    window = glfwGetCurrentContext()
                    pos = glfwGetCursorPos(window)
                    pos = normalize(pos,glfwGetWindowSize(window),flip_y=True)
                    for s,v_idx in self.edit_surf_verts:
                        if s.detected:
                            new_pos = s.img_to_ref_surface(np.array(pos))
                            s.move_vertex(v_idx,new_pos)

logging.disable(logging.WARNING)

# modified version of offline_marker_detector
# first will look into Offline_Surface_Tracker namespaces then Screen_Tracker and so on
class Screen_Tracker_Offline(Offline_Surface_Tracker,Screen_Tracker):
    """
    Special version of screen tracker for use with videofile source.
    It will search all frames in the world.avi file for screens.
     - self.cache is a list containing marker positions for each frame.
     - self.surfaces[i].cache is a list containing surface positions for each frame
    Both caches are build up explicitly by pressing buttons.
    The cache is also session persistent.
    See marker_tracker.py for more info on this marker tracker.
    """
    def __init__(self,*args, **kwargs):
        self.screen_x = 1 
        self.screen_y = 1
        for name, value in kwargs.items():
            if name == 'screen_x':
                self.screen_x = value
            if name == 'screen_y':
                self.screen_y = value
        super().__init__(*args,"Show Markers and Surfaces",100,False,True)
        
    def load_surface_definitions_from_file(self):
        self.surface_definitions = Persistent_Dict(os.path.join(self.g_pool.rec_dir,'screen_definition'))
        if self.surface_definitions.get('offline_square_marker_surfaces',[]) != []:
            logger.debug("Found screen defined or copied in previous session.")
            self.surfaces = [Offline_Reference_Surface(self.g_pool,saved_definition=d) for d in self.surface_definitions.get('offline_square_marker_surfaces',[]) if isinstance(d,dict)]
        elif self.surface_definitions.get('realtime_square_marker_surfaces',[]) != []:
            logger.debug("Did not find any screen in player from earlier session. Loading surfaces defined during capture.")
            self.surfaces = [Offline_Reference_Surface(self.g_pool,saved_definition=d) for d in self.surface_definitions.get('realtime_square_marker_surfaces',[]) if isinstance(d,dict)]
        else:
            logger.debug("No screen found. Please define using GUI.")
            self.surfaces = []

    def init_ui(self):
        super().init_ui()
        self.menu.label = 'Screen Tracker (Offline)'
  
    def init_marker_cacher(self):
        pass

    def update_marker_cache(self):
        pass

    def close_marker_cacher(self):
        pass

    def seek_marker_cacher(self,idx):
        pass

    def update_cache_hack(self):
        from video_capture import File_Source, EndofVideoError, FileSeekError
        
        def put_in_cache(frame_idx,detected_screen):
            print(frame_idx)
            visited_list[frame_idx] = True
            self.cache.update(frame_idx,detected_screen)
            for s in self.surfaces:
                s.update_cache(self.cache,
                    min_marker_perimeter=self.min_marker_perimeter,
                    min_id_confidence=self.min_id_confidence,
                    idx=frame_idx)
            
        def next_unvisited_idx(frame_idx):
            try:
                visited = visited_list[frame_idx]
            except IndexError:
                visited = True # trigger search

            if not visited:
                next_unvisited = frame_idx
            else:
                # find next unvisited site in the future
                try:
                    next_unvisited = visited_list.index(False,frame_idx)
                except ValueError:
                    # any thing in the past?
                    try:
                        next_unvisited = visited_list.index(False,0,frame_idx)
                    except ValueError:
                        #no unvisited sites left. Done!
                        #logger.debug("Caching completed.")
                        next_unvisited = None
            return next_unvisited

        def handle_frame(next_frame):
            if next_frame != cap.get_frame_index():
                #we need to seek:
                #logger.debug("Seeking to Frame %s" %next_frame)
                try:
                    cap.seek_to_frame(next_frame)
                except FileSeekError:
                    put_in_cache(next_frame,[]) # we cannot look at the frame, report no detection
                    return
                #seeking invalidates prev markers for the detector
                # markers[:] = []
            
            try:
                frame = cap.get_frame()
            except EndofVideoError:
                put_in_cache(next_frame,[]) # we cannot look at the frame, report no detection
                return

            put_in_cache(frame.index,detect_screens(frame.gray))

        self.cacher_seek_idx = 0
        visited_list = [False for x in self.cache]
        # markers = []
        cap = File_Source(Global_Container(),self.g_pool.capture.source_path)

        for _ in self.cache:
            next_frame = cap.get_frame_index()
            if next_frame is None or next_frame >=len(self.cache):
                #we are done here:
                break
            else:
                handle_frame(next_frame)

    def update_gui_markers(self):

        def close():
            self.alive = False

        self.menu.elements[:] = []
        self.menu.append(ui.Button('Close', close))
        self.menu.append(ui.Info_Text('The offline screen tracker will look for a screen for each frame of the video. By default it uses surfaces defined in capture. You can change and add more surfaces here.'))

        self.menu.append(ui.Info_Text('Before starting, you must update the screen detector cache:'))
        self.menu.append(ui.Button("Update Cache", self.update_cache_hack))            

        self.menu.append(ui.Info_Text('Then you can add a screen. Move to a frame where the screen was detected (in blue) then press the add screen surface button.'))
        self.menu.append(ui.Button("Add screen surface",lambda:self.add_surface()))

        self.menu.append(ui.Info_Text("Press the export button to export data from the current section."))

        for s in self.surfaces:
            idx = self.surfaces.index(s)
            s_menu = ui.Growing_Menu("Surface %s"%idx)
            s_menu.collapsed=True
            s_menu.append(ui.Text_Input('name',s))
            s_menu.append(ui.Text_Input('x',s.real_world_size,label='X size (width)'))
            s_menu.append(ui.Text_Input('y',s.real_world_size,label='Y size (height)'))
            s_menu.append(ui.Button('Open Debug Window',s.open_close_window))
            #closure to encapsulate idx
            def make_remove_s(i):
                return lambda: self.remove_surface(i)
            remove_s = make_remove_s(idx)
            s_menu.append(ui.Button('remove',remove_s))
            self.menu.append(s_menu)

    def remove_surface(self, i):
        remove_surface = self.surfaces[i]
        if remove_surface == self.marker_edit_surface:
            self.marker_edit_surface = None
        if remove_surface in self.edit_surfaces:
            self.edit_surfaces.remove(remove_surface)

        self.surfaces[i].cleanup()
        del self.surfaces[i]
        self.update_gui_markers()
        self.notify_all({'subject': 'surfaces_changed'})
        self.timeline.content_height -= self.timeline_line_height

    def add_surface(self):
        self.surfaces.append(Offline_Reference_Surface(self.g_pool))
        self.timeline.content_height += self.timeline_line_height

        self.surfaces[0].name = 'Screen'
        self.surfaces[0].real_world_size['x'] = self.screen_x
        self.surfaces[0].real_world_size['y'] = self.screen_y
        self.update_gui_markers()

    def get_init_dict(self):
        return {
            'screen_x':self.screen_x,
            'screen_y':self.screen_y
        }

    def on_notify(self,notification):
        if notification['subject'] == "should_export":
            self.recalculate()
            self.save_surface_statsics_to_file(notification['range'],notification['export_dir'])

del Surface_Tracker
del Screen_Tracker
del Offline_Surface_Tracker