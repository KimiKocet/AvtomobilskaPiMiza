import math
from time import time

from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.graphics import Color, Line, Ellipse, RoundedRectangle, Rectangle
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton

from widgets.MediaPanel import MediaPanel
from widgets.SpeedRpmGauge import SpeedRpmGauge

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        container = BoxLayout(orientation='horizontal', spacing=dp(30), padding=dp(30))
        self.gauge = SpeedRpmGauge(size_hint=(0.55, 1))
        media_anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(0.45, 1))
        self.media_panel = MediaPanel()
        media_anchor.add_widget(self.media_panel)
        container.add_widget(self.gauge)
        container.add_widget(media_anchor)
        self.add_widget(container)

        Clock.schedule_interval(self.demo_animation, 1.0 / 60.0)
        self.anim_dir = 1

    def demo_animation(self, dt):
        if self.gauge.rpm >= 6500: self.anim_dir = -1
        if self.gauge.rpm <= 800: self.anim_dir = 1
        self.gauge.rpm += (40 * self.anim_dir)
        self.gauge.speed = self.gauge.rpm / 35
