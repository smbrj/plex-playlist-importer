from plex_playlist.plex_client import PlexClient

class Item:
    def __init__(self, key): self.ratingKey = key
class Playlist:
    def __init__(self, items): self._items=list(items); self.removed=[]
    def items(self): return list(self._items)
    def removeItems(self, items):
        for item in list(items):
            self.removed.append(item)
            self._items.remove(item)

def make_client(items):
    client=object.__new__(PlexClient)
    pl=Playlist(items)
    client.get_playlist=lambda name: pl
    return client,pl

def test_fifo_removes_front_occurrence_only():
    a1,b,a2,c=Item('a1'),Item('b'),Item('a2'),Item('c')
    client,pl=make_client([a1,b,a2,c])
    result=client.trim_playlist_fifo(name='x',max_tracks=3)
    assert pl.removed == [a1]
    assert pl.items() == [b,a2,c]
    assert result == {'current':4,'removed':1,'final':3}

def test_repairs_oversized():
    items=[Item(str(i)) for i in range(6)]
    client,pl=make_client(items)
    result=client.trim_playlist_fifo(name='x',max_tracks=4)
    assert pl.removed == items[:2]
    assert result['final']==4

def test_zero_noop():
    items=[Item('1'),Item('2')]
    client,pl=make_client(items)
    result=client.trim_playlist_fifo(name='x',max_tracks=0)
    assert pl.removed == []
    assert result['final']==2

def test_trim_retries_stale_plex_read(monkeypatch):
    old = Item("old")
    new = Item("new")

    original = Playlist([old, new])
    stale = Playlist([old, new])
    fresh = Playlist([new])

    responses = iter([
        original,  # initial playlist used for removal
        stale,     # first verification read is stale
        fresh,     # next verification sees completed removal
    ])

    client = object.__new__(PlexClient)
    client.get_playlist = lambda name: next(responses)

    monkeypatch.setattr(
        "plex_playlist.plex_client.time.sleep",
        lambda seconds: None,
    )

    result = client.trim_playlist_fifo(
        name="x",
        max_tracks=1,
    )

    assert original.removed == [old]
    assert result == {
        "current": 2,
        "removed": 1,
        "final": 1,
    }