from __future__ import annotations
from dataclasses import dataclass
import subprocess

from flask import Flask, redirect, render_template, url_for


def run_command(command: str) -> str:
    """
    Run a command and returns its stdout.
    Raise a RuntimeError if the command returns an error.
    """
    p = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    err = p.stderr.read()
    if err:
        print(err.decode("utf-8"))
        raise RuntimeError(f"command {command} provoqued an error")
    return p.stdout.read().decode("utf-8")


@dataclass
class MocpInfos:
    """
    Holds the status of MOCP.
    Since I can't find a way to get playlist infos from command line,
    it just knows about the currently playing song.
    """

    is_playing: bool
    title: str
    artist: str
    album: str
    total_time: int
    current_time: int
    volume: int

    @classmethod
    def from_infos(cls) -> MocpInfos:
        """Return a new instance read from command line."""
        lines = MocpControler.infos().splitlines()
        pairs = map(lambda line: line.split(":"), lines)
        dict_infos = {pair[0]: pair[1] for pair in pairs}
        volume = int(MocpControler.get_volume())
        return cls(
            dict_infos.get("State", "PAUSE").strip() == "PLAY",
            dict_infos.get("Title", "Unknown title"),
            dict_infos.get("Artist", "Unknown artist"),
            dict_infos.get("Album", "Unknown album"),
            int(dict_infos.get("TotalSec", 1)),
            int(dict_infos.get("CurrentSec", 0)),
            volume,
        )

    def update(self) -> None:
        """Update itself with new infos"""
        new = self.from_infos()
        self.is_playing = new.is_playing
        self.title = new.title
        self.artist = new.artist
        self.album = new.album
        self.total_time = new.total_time
        self.current_time = new.current_time
        self.volume = new.volume


class MocpControler:
    @staticmethod
    def toggle_pause() -> None:
        run_command("mocp -G")

    @staticmethod
    def previous_song() -> None:
        run_command("mocp -r")

    @staticmethod
    def next_song() -> None:
        run_command("mocp -f")

    @staticmethod
    def infos() -> str:
        return run_command("mocp -i")

    @staticmethod
    def volume_up():
        run_command("mocp -v +10")

    @staticmethod
    def volume_down():
        run_command("mocp -v -10")

    @staticmethod
    def get_volume():
        return run_command(
            r"""pactl list sinks | grep '^[[:space:]]Volume:' | \
head -n $(( $SINK + 1 )) | tail -n 1 | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'
        """
        )


app = Flask(__name__)


@app.route("/")
def index():
    infos.update()
    return render_template("index.html", infos=infos)


@app.route("/previous_song", methods=["POST"])
def previous_song():
    MocpControler.previous_song()
    return redirect(url_for("index"))


@app.route("/toggle_pause", methods=["POST"])
def toggle_pause():
    MocpControler.toggle_pause()
    return redirect(url_for("index"))


@app.route("/next_song", methods=["POST"])
def next_song():
    MocpControler.next_song()
    return redirect(url_for("index"))


@app.route("/volume_down", methods=["POST"])
def volume_down():
    MocpControler.volume_down()
    return redirect(url_for("index"))


@app.route("/volume_up", methods=["POST"])
def volume_up():
    MocpControler.volume_up()
    return redirect(url_for("index"))


infos = MocpInfos.from_infos()

app.run(debug=True, port=2222, host="0.0.0.0")
