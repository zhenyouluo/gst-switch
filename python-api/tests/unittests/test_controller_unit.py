"""Unittests for Controller class in controller.py"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "../../../")))

from gstswitch.controller import Controller
from gstswitch.exception import ConnectionReturnError
import pytest
from mock import Mock
from gstswitch.connection import Connection
from gi.repository import GLib


class TestAddress(object):

    """Test the address parameter"""

    def test_address_null(self):
        """Test if address is null"""
        address = ['', None, [], {}]
        for addr in address:
            with pytest.raises(ValueError):
                Controller(address=addr)

    def test_address_colon(self):
        """Test if address has no colon"""
        address = 'abcdefghijk'
        with pytest.raises(ValueError):
            Controller(address=address)

    def test_address_normal(self):
        """Test if address is valid"""
        address = ['tcp:host=127.0.0.1,port=5000', 'unix:temp=/tmp/abcd/xyz']
        for addr in address:
            conn = Controller(address=addr)
            assert conn.address == addr


class TestBusName(object):

    """Test bus_name parameter"""

    def test_normal(self):
        """Test when bus_name is not null"""
        names = ['', 'abcd', 12345]
        for bus in names:
            conn = Controller(bus_name=bus)
            assert conn.bus_name == str(bus)

    def test_normal_none(self):
        """Test when bus_name is null"""
        name = None
        conn = Controller(bus_name=name)
        assert conn.bus_name == name


class TestObjectPath(object):

    """Test object_path parameter"""

    def test_object_path_blank(self):
        """Test when the object_path is null"""
        paths = [None, '', {}, []]
        for object_path in paths:
            with pytest.raises(ValueError):
                Controller(object_path=object_path)

    def test_object_path_slash(self):
        """Test when object_path doesn't have slash in start"""
        object_path = 'a/////////'
        with pytest.raises(ValueError):
            Controller(object_path=object_path)

    def test_object_path_normal(self):
        """Test when object_path is valid"""
        object_path = "/us/timvideos/gstswitch/SwitchController"
        conn = Controller(object_path=object_path)
        assert conn.object_path == object_path


class TestInterface(object):

    """Test the default_interface parameter"""

    def test_interface_none(self):
        """Test when the default_interface is null"""
        default_interface = [None, '', [], {}]
        for interface in default_interface:
            with pytest.raises(ValueError):
                Controller(default_interface=interface)

    def test_interface_dot(self):
        """Test when the default_interface has <2 dots"""
        default_interface = ['.', 'info.', 'info']
        for interface in default_interface:
            with pytest.raises(ValueError):
                Controller(default_interface=interface)

    def test_interface_normal(self):
        """Test when the interface is valid"""
        default_interface = "us.timvideos.gstswitch.SwitchControllerInterface"
        conn = Controller(default_interface=default_interface)
        assert default_interface == conn.default_interface


class TestEstablishConnection(object):

    """Test the establish_connection method"""

    def test_normal(self, monkeypatch):
        """Test if the parameters are valid"""
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())
        monkeypatch.setattr(Connection, 'signal_subscribe', Mock())
        controller = Controller(address='unix:abstract=abcd')
        controller.establish_connection()
        assert controller.connection is not None


class TestSignalHandler(object):

    """Test the cb_signal_handler method"""

    def test_unknown_signal_name(self, monkeypatch):
        """Test that nothing happens when a unknown signal is on the bus"""
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())
        controller = Controller(address='unix:abstract=abcd')
        controller.cb_signal_handler(None, ':0', '/foo/bar',
                                     'foo.bar', 'foobar', None, None)

    def test_signal_name_collision(self, monkeypatch):
        """Test that nothing happens when a signal is on the bus which name
        collides with an attribute also starting with 'callbacks_'
        """
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())
        controller = Controller(address='unix:abstract=abcd')
        controller.callbacks_foobar = 123
        controller.cb_signal_handler(None, ':0', '/foo/bar',
                                     'foo.bar', 'foobar', None, None)

    def test_invalid_callback(self, monkeypatch):
        """Test that a ValueError is raised when a not-callable object is
        registered as callback-handler
        """
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())

        for signal in ('preview_port_added', 'preview_port_removed',
                       'new_mode_online', 'show_face_marker',
                       'show_track_marker', 'select_face'):
            test_cb = 123
            controller = Controller(address='unix:abstract=abcd')
            with pytest.raises(ValueError):
                getattr(controller, 'on_' + signal)(test_cb)

    def test_single_handler_calls(self, monkeypatch):
        """Test that the various Handler gets calles"""
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())

        for signal in ('preview_port_added', 'preview_port_removed',
                       'new_mode_online', 'show_face_marker',
                       'show_track_marker', 'select_face'):
            test_cb = Mock()
            controller = Controller(address='unix:abstract=abcd')
            getattr(controller, 'on_' + signal)(test_cb)

            controller.cb_signal_handler(
                None,
                ':0',
                '/us/timvideos/gstswitch/SwitchControllerInterface',
                'us.timvideos.gstswitch.SwitchControllerInterface',
                signal,
                GLib.Variant('(iii)', (5, 10, 20,)),
                None)
            test_cb.assert_called_once_with(5, 10, 20)

    def test_multiple_handler_calls(self, monkeypatch):
        """Test that the various Handler gets calles"""
        monkeypatch.setattr(Connection, 'connect_dbus', Mock())
        controller = Controller(address='unix:abstract=abcd')

        signals = ('preview_port_added', 'preview_port_removed',
                   'new_mode_online', 'show_face_marker',
                   'show_track_marker', 'select_face')
        test_cbs = {}
        for signal in signals:
            test_cbs[signal] = Mock()
            getattr(controller, 'on_' + signal)(test_cbs[signal])
            getattr(controller, 'on_' + signal)(test_cbs[signal])
            getattr(controller, 'on_' + signal)(test_cbs[signal])

        for signal in signals:
            controller.cb_signal_handler(
                None,
                ':0',
                '/us/timvideos/gstswitch/SwitchControllerInterface',
                'us.timvideos.gstswitch.SwitchControllerInterface',
                signal,
                GLib.Variant('(i)', (123,)),
                None)

        for signal in signals:
            test_cbs[signal].assert_called_with(123)
            assert test_cbs[signal].call_count == 3


class MockConnection(object):

    """A class which mocks the Connection class"""

    def __init__(self, return_variant, should_fail=False):
        """Create an Instance of class which mocks the Connection class

        Attributes:
          return_variant (bool): Indicates whether the get_*-Methods
            should wrap the return-value into a GLib.Variant or return
            the native values
          should_fail (bool): Indicates if the action-Methotds
            (ie set_encode_mode) should return a Value indicating a
            failure or a success.
        """

        self.return_variant = return_variant
        self.should_fail = should_fail

    def get_compose_port(self):
        """mock of get_compose_port"""
        if self.return_variant:
            return GLib.Variant('(i)', (3001,))
        else:
            return (0,)

    def get_encode_port(self):
        """mock of get_encode_port"""
        if self.return_variant:
            return GLib.Variant('(i)', (3002,))
        else:
            return (0,)

    def get_audio_port(self):
        """mock of get_audio_port"""
        if self.return_variant:
            return GLib.Variant('(i)', (4000,))
        else:
            return (0,)

    def get_preview_ports(self):
        """mock of get_preview_ports"""
        if self.return_variant:
            return GLib.Variant('(s)', ('[(3002, 1, 7), (3003, 1, 8)]',))
        else:
            return (0,)

    def set_composite_mode(self, mode):
        """mock of set_composite_mode"""
        if self.return_variant:
            return GLib.Variant('(b)', (not self.should_fail,))
        else:
            return (not self.should_fail,)

    def get_composite_mode(self):
        """mock of set_composite_mode"""
        if self.return_variant:
            return GLib.Variant('(i)', (0,))
        else:
            return (0,)

    def set_encode_mode(self, mode):
        """mock of get_set_encode_mode"""
        if self.return_variant:
            return GLib.Variant('(b)', (not self.should_fail,))
        else:
            return (not self.should_fail,)

    def new_record(self):
        """mock of new_record"""
        if self.return_variant:
            return GLib.Variant('(b)', (not self.should_fail,))
        else:
            return (not self.should_fail,)

    def adjust_pip(self, xpos, ypos, width, height):
        """mock of adjust_pip"""
        if self.return_variant:
            return GLib.Variant('(u)', (1,))
        else:
            return (1,)

    def switch(self, channel, port):
        """mock of switch"""
        if self.return_variant:
            return GLib.Variant('(b)', (not self.should_fail,))
        else:
            return (not self.should_fail,)

    def click_video(self, xpos, ypos, width, height):
        """mock of click_video"""
        if self.return_variant:
            return GLib.Variant('(b)', (not self.should_fail,))
        else:
            return (not self.should_fail,)

    def mark_face(self, face):
        """mock of mark_face"""
        pass

    def mark_tracking(self, face):
        """mock of mark_tracking"""
        pass


class TestGetComposePort(object):

    """Test the get_compose_port method"""

    def test_unpack(self):
        """Test when values cant unpack"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.get_compose_port()

    def test_normal_unpack(self):
        """Test when valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.connection = MockConnection(return_variant=True)
        assert controller.get_compose_port() == 3001


class TestGetEncodePort(object):

    """Test the get_encode_port method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.get_encode_port()

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.connection = MockConnection(return_variant=True)
        assert controller.get_encode_port() == 3002


class TestGetAudioPort(object):

    """ Test the get_audio_port method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.get_audio_port()

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.connection = MockConnection(return_variant=True)
        assert controller.get_audio_port() == 4000


class TestGetPreviewPorts(object):

    """Test the get_preview_ports method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.get_preview_ports()

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.connection = MockConnection(return_variant=True)
        controller.parse_preview_ports = Mock(return_value=[3001, 3002])
        assert controller.get_preview_ports() == [3001, 3002]


class TestSetCompositeMode(object):

    """Test the set_composite_mode method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.set_composite_mode(Controller.COMPOSITE_NONE)

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.set_composite_mode(Controller.COMPOSITE_NONE) is True


class TestGetCompositeMode(object):

    """Test the get_composite_mode method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcdefghijk')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.get_composite_mode()

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.get_composite_mode() is Controller.COMPOSITE_NONE


class TestSetEncodeMode(object):

    """Test the set_encode_mode method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.set_encode_mode(1)

    def test_action_fails(self):
        """Test what happens if the requested action fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(
            return_variant=True, should_fail=True)
        assert controller.set_encode_mode(1) is False

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.set_encode_mode(1) is True


class TestNewRecord(object):

    """Test the new_record method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.new_record()

    def test_action_fails(self):
        """Test what happens if the requested action fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(
            return_variant=True, should_fail=True)
        assert controller.new_record() is False

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.new_record() is True


class TestAdjustPIP(object):

    """Test the adjust_pip method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.adjust_pip(1, 2, 3, 4)

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.adjust_pip(1, 2, 3, 4) == 1


class TestSwitch(object):

    """Test the switch method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.switch(Controller.VIDEO_CHANNEL_A, 2)

    def test_action_fails(self):
        """Test what happens if the requested action fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(
            return_variant=True, should_fail=True)
        assert controller.switch(Controller.VIDEO_CHANNEL_A, 2) is False

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.switch(Controller.VIDEO_CHANNEL_A, 2) is True


class TestClickVideo(object):

    """Test the click_video method"""

    def test_unpack(self):
        """Test if unpack fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        with pytest.raises(ConnectionReturnError):
            controller.click_video(1, 2, 3, 4)

    def test_action_fails(self):
        """Test what happens if the requested action fails"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(
            return_variant=True, should_fail=True)
        assert controller.click_video(1, 2, 3, 4) is False

    def test_normal_unpack(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcdef')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=True)
        assert controller.click_video(1, 2, 3, 4) is True


class TestMarkFaces(object):

    """Tes the mark_face method"""

    def test_normal(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        face = [(1, 2, 3, 4), (1, 1, 1, 1)]
        controller.mark_face(face)


class TestMarkTracking(object):

    """Test the mark_tracking method"""

    def test_normal(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcde')
        controller.establish_connection = Mock(return_value=None)
        controller.connection = MockConnection(return_variant=False)
        face = [(1, 2, 3, 4), (1, 1, 1, 1)]
        controller.mark_tracking(face)


class TestParsePreviewPorts(object):

    """Test the parse_preview_ports class method"""

    def test_value_error(self):
        """Test if invalid"""
        controller = Controller(address='unix:abstract=abcde')
        test = 1234
        with pytest.raises(ConnectionReturnError):
            controller.parse_preview_ports(test)

    def test_syntax_error(self):
        """Test if syntax error detected"""
        controller = Controller(address='unix:abstract=abcde')
        test = '{}[]'
        with pytest.raises(ConnectionReturnError):
            controller.parse_preview_ports(test)

    def test_normal(self):
        """Test if valid"""
        controller = Controller(address='unix:abstract=abcde')
        test = '[(1, 2, 3), (2, 2, 2)]'
        assert controller.parse_preview_ports(test) == [1, 2]
