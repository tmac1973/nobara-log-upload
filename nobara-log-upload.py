import json
import gi
import pathlib
import tempfile
import subprocess
from systemd import journal
from datetime import datetime, timedelta

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

def get_systemd_logs(delta_minutes: int) -> list[str]:
    logs = []
    j = journal.Reader()
    j.seek_realtime(datetime.now() - timedelta(minutes=delta_minutes))
    for entry in j:
        logs.append(entry['MESSAGE'])
    return logs

def get_txt_file(filepath: pathlib.Path) -> list[str]:
    logs = []
    with filepath.open(mode="r") as file:
        for line in file:
            logs.append(line.rstrip())
    return logs

def get_systemd_logs_15() -> list[str]:
    return get_systemd_logs(15)

def get_nobara_sync_log() -> list[str]:

    logpath = pathlib.PosixPath("~/.local/share/nobara-updater/nobara-sync.log")
    logfile = logpath.expanduser()
    logs = None
    try:
        logs = get_txt_file(logfile)
    except FileNotFoundError:
        print(f"Could not find nobara-sync logfile: {logfile}")
    return logs

def merge_string_list(strings : list[str]) -> str:
    return '\n'.join(strings)

def upload_textfile(text: str) -> str:
    second = ""
    try:
        first = subprocess.Popen(['/bin/echo', text], stdout=subprocess.PIPE)
        second = subprocess.Popen(['/usr/bin/pbcli', '--json'], stdin=first.stdout, stdout=subprocess.PIPE)
    except Exception as e:
        print(f"Could not execute pbcli\n{str(e)}")
    result, _ = second.communicate()
    return result


LIST_ENTRIES = [
    {'name': 'System Log', 'enabled': True, 'func' : get_systemd_logs_15},
    {'name': 'nobara-sync log', 'enabled': True, 'func': get_nobara_sync_log},
]

class MyWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nobara Log Uploader")
        self.set_default_size(300, -1)
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box_outer.set_size_request(300, -1)
        self.add(box_outer)
        hbox = Gtk.Box(spacing=50)
        label = Gtk.Label(label="Send which files to the dumpsterfire?")
        hbox.add(label)
        box_outer.add(hbox)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box_outer.add(separator)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.entry_count = 0
        for entry in LIST_ENTRIES:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add(hbox)
            label = Gtk.Label(label=entry['name'], xalign=0)
            check = Gtk.CheckButton()
            check.set_active(entry['enabled'])
            hbox.pack_start(label, True, True, 0)
            hbox.pack_start(check, False, True, 0)
            row.func = entry['func']
            self.listbox.add(row)
            self.entry_count=+1


        box_outer.pack_start(self.listbox, True, True, 0)
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box_outer.add(separator2)

        hbox = Gtk.Box(spacing=50)
        button = Gtk.Button.new_with_label("Upload")
        button.connect("clicked", self.on_upload_clicked)
        hbox.pack_start(button, True, True, 0)
        box_outer.add(hbox)

    def dialog(self, title:str, msg:str ):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        content_area = dialog.get_content_area()

        # Create a Gtk.Label for the text.  Critically, *do not* use
        # dialog.format_secondary_text, as that adds a *non*-selectable
        # label.
        label = Gtk.Label(label=msg)

        # Set properties to make the text selectable
        label.set_selectable(True)
        label.set_line_wrap(False)  # Enable line wrapping for longer text
        # label.set_xalign(0)  # Align the text to the left within the label
        # label.set_yalign(0)  # Align the text to the top
        # Add some padding.
        label.set_margin_top(12)
        label.set_margin_bottom(12)
        label.set_margin_left(12)
        label.set_margin_right(12)

        # Add the Gtk.Label to the content area of the dialog
        content_area.pack_start(label, True, True, 0)
        #  Show the label explicitly.
        label.show()
        dialog.run()

    def on_upload_clicked(self, button):
        logs = []
        for row in self.listbox.get_children():
            if isinstance(row, Gtk.ListBoxRow):
                children = row.get_children()[0].get_children()
                if isinstance(children[1], Gtk.CheckButton):
                    checkbutton = children[1]
                    if checkbutton.get_active():
                        print(f"calling {row.func}")
                        logs.append(merge_string_list(row.func()))
        logblob = merge_string_list(logs)
        upload_results = upload_textfile(logblob)
        results_json = json.loads(upload_results)
        print(results_json)
        self.dialog("Paste URL", results_json['pasteurl'])


def main():
    win = MyWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()