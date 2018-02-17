
from gi.repository import Gtk, Gdk

from pychess.Utils.const import BLACK, WHITE
from pychess.Utils.GameModel import GameModel
from pychess.perspectives import perspective_manager
from pychess.Utils.elo import get_elo_rating_change_str
from pychess.widgets import mainwindow

firstRun = True
tags_store = Gtk.ListStore(str, str)
dedicated_tags = ['Site', 'Event', 'Date', 'Round', 'Annotator', 'White', 'Black', 'WhiteElo', 'BlackElo']


def run(widgets):
    global firstRun, tags_store, dedicated_tags

    # Data from the game
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    # Initialization
    if firstRun:
        initialize(widgets)
        firstRun = False

    # Load of the tags having a dedicated field
    for tag in dedicated_tags:
        widgets["%s_entry" % tag.lower()].set_text(str(gamemodel.getTag(tag, "")))
    refresh_elo_rating_change(widgets)

    # Load of the tags in the editor
    tags_store.clear()
    for tag in gamemodel.tags:
        if tag not in dedicated_tags and isinstance(gamemodel.tags[tag], str):
            tags_store.append([tag, gamemodel.tags[tag]])

    # Show the loaded dialog
    widgets["game_info"].show()


def initialize(widgets):
    def hide_window(button, *args):
        widgets["game_info"].hide()
        return True

    def on_pick_date(button, *args):
        # Parse the existing date
        obj = GameModel()
        obj.tags = {"Date": widgets["date_entry"].get_text()}
        year, month, day = obj.getGameDate()

        # Prepare the date of the picker
        calendar = Gtk.Calendar()
        curyear, curmonth, curday = calendar.get_date()
        try:
            year = int(year)
        except ValueError:
            year = curyear
        try:
            month = int(month) - 1
        except ValueError:
            month = curmonth
        try:
            day = int(day)
        except ValueError:
            day = curday
        calendar.select_month(month, year)
        calendar.select_day(day)

        # Show the dialog
        dialog = Gtk.Dialog(_("Pick a date"),
                            mainwindow(),
                            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(calendar)

        dialog.get_content_area().pack_start(sw, True, True, 0)
        dialog.resize(300, 200)
        dialog.show_all()

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            year, month, day = calendar.get_date()
            widgets["date_entry"].set_text("%04d.%02d.%02d" % (year, month + 1, day))

    def on_add_tag(button, *args):
        tv_iter = tags_store.append([_("New"), ""])
        path = tags_store.get_path(tv_iter)
        widgets["tags_treeview"].set_cursor(path)

    def on_delete_tag(button, *args):
        store, tv_iter = widgets["tags_treeview"].get_selection().get_selected()
        if tv_iter:
            store.remove(tv_iter)

    def accept_new_properties(button, *args):
        persp = perspective_manager.get_perspective("games")
        gamemodel = persp.cur_gmwidg().gamemodel

        # Remove the existing tags in string format
        for tag in list(gamemodel.tags):
            if isinstance(gamemodel.tags[tag], str):
                del gamemodel.tags[tag]

        # Copy of the tags from the dedicated fields
        for tag in dedicated_tags:
            gamemodel.tags[tag] = widgets["%s_entry" % tag.lower()].get_text()

        # Copy the extra tags from the editor
        for tag in tags_store:
            if tag[0] != "" and tag not in dedicated_tags:
                gamemodel.tags[tag[0]] = tag[1]

        widgets["game_info"].hide()

        # Apply some settings to the game model
        gamemodel.players[BLACK].setName(gamemodel.tags["Black"])
        gamemodel.players[WHITE].setName(gamemodel.tags["White"])
        gamemodel.emit("players_changed")
        return True

    # Tag editor
    def tag_edited_cb(cell, path, new_text):
        global tags_store
        tags_store[path][0] = new_text

    def value_edited_cb(cell, path, new_text):
        global tags_store
        tags_store[path][1] = new_text

    global tags_store
    tv_tags = widgets["tags_treeview"]
    tv_tags.set_model(tags_store)

    tag_renderer = Gtk.CellRendererText()
    tag_renderer.set_property("editable", True)
    tag_renderer.connect("edited", tag_edited_cb)
    tv_tags.append_column(Gtk.TreeViewColumn("Tag", tag_renderer, text=0))

    value_renderer = Gtk.CellRendererText()
    value_renderer.set_property("editable", True)
    value_renderer.connect("edited", value_edited_cb)
    tv_tags.append_column(Gtk.TreeViewColumn("Value", value_renderer, text=1))

    # Events on the UI
    widgets["whiteelo_entry"].connect("changed", lambda p: refresh_elo_rating_change(widgets))
    widgets["blackelo_entry"].connect("changed", lambda p: refresh_elo_rating_change(widgets))
    widgets["date_button"].connect("clicked", on_pick_date)
    widgets["tag_add_button"].connect("clicked", on_add_tag)
    widgets["tag_delete_button"].connect("clicked", on_delete_tag)
    widgets["game_info"].connect("delete-event", hide_window)
    widgets["game_info_cancel_button"].connect("clicked", hide_window)
    widgets["game_info_ok_button"].connect("clicked", accept_new_properties)


red = Gdk.RGBA(.643, 0, 0, 1)
green = Gdk.RGBA(.306, .604, .024, 1)
black = Gdk.RGBA(0.0, 0.0, 0.0, 1.0)


def refresh_elo_rating_change(widgets):
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    site = gamemodel.tags["Site"]
    if "lichess.org" in site or "chessclub.com" in site or "freechess.org" in site:
        # TODO : lichess takes 3 parameters per player
        widgets["w_elo_change"].set_text("")
        widgets["b_elo_change"].set_text("")
        return

    welo = widgets["whiteelo_entry"].get_text()
    belo = widgets["blackelo_entry"].get_text()

    wchange = get_elo_rating_change_str(gamemodel, WHITE, welo, belo)
    widgets["w_elo_change"].set_text(wchange)
    if wchange.startswith("+") or wchange.startswith("-"):
        widgets["w_elo_change"].override_color(Gtk.StateFlags.NORMAL, red if wchange.startswith("-") else green)
    else:
        widgets["w_elo_change"].override_color(Gtk.StateFlags.NORMAL, black)

    bchange = get_elo_rating_change_str(gamemodel, BLACK, welo, belo)
    widgets["b_elo_change"].set_text(bchange)
    if bchange.startswith("+") or bchange.startswith("-"):
        widgets["b_elo_change"].override_color(Gtk.StateFlags.NORMAL, red if bchange.startswith("-") else green)
    else:
        widgets["b_elo_change"].override_color(Gtk.StateFlags.NORMAL, black)
