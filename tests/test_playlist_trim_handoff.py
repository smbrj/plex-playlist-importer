from dataclasses import dataclass
from plex_playlist.playlist_trim import filter_tidal_reconciliation_for_final_plex_membership
from plex_playlist.tidal_reconcile import TidalReconcileAction

@dataclass
class TrackState:
    artist:str
    title:str
@dataclass
class Decision:
    track_id:str
    action:object
class Store:
    def __init__(self, mapping): self.mapping=mapping
    def get_track(self, track_id): return self.mapping.get(track_id)
class PlexItem:
    def __init__(self,artist,title): self.grandparentTitle=artist; self.title=title

def test_destructive_allowed_when_final_plex_contains_replacement():
    d=Decision('1',TidalReconcileAction.REMOVE_FROM_PLAYLIST_AND_FAVORITES)
    out=filter_tidal_reconciliation_for_final_plex_membership(
        decisions=[d],state_store=Store({'1':TrackState('69 Boyz','Tootsee Roll')}),
        playlist_items=[PlexItem('69 Boyz','Tootsee Roll')],artist_aliases={})
    assert out == [d]

def test_destructive_suppressed_when_trim_removed_replacement():
    d=Decision('1',TidalReconcileAction.REMOVE_FROM_PLAYLIST_AND_FAVORITES)
    out=filter_tidal_reconciliation_for_final_plex_membership(
        decisions=[d],state_store=Store({'1':TrackState('69 Boyz','Tootsee Roll')}),
        playlist_items=[PlexItem('Other','Song')],artist_aliases={})
    assert out == []

def test_keep_is_preserved_without_local_membership():
    d=Decision('1',TidalReconcileAction.KEEP)
    out=filter_tidal_reconciliation_for_final_plex_membership(
        decisions=[d],state_store=Store({}),playlist_items=[],artist_aliases={})
    assert out == [d]
