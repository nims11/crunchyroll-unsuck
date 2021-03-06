""" Extending crunchyroll api implemented in streamlink
"""
import json
from enum import Enum
from typing import Optional, Dict, Any, List

import requests
from streamlink.session import Streamlink


class MediaType(Enum):
    ANIME = "anime"
    DRAMA = "drama"
    ANIMEDRAMA = "anime|drama"


class Filters(Enum):
    ALPHA = "alpha"
    FEATURED = "featured"
    NEWEST = "newest"
    POPULAR = "popular"
    PREFIX = "prefix:"
    SIMULCAST = "simulcast"
    TAG = "tag:"
    UPDATED = "updated"


class SortOption(Enum):
    ASC = "asc"
    DESC = "desc"


CR_AJAX_ANIME_LIST = 'http://www.crunchyroll.com/ajax/?req=RpcApiSearch_GetSearchCandidates'


class CrunchyrollAPI:
    @staticmethod
    def _create_api(username: str, password: str):
        """ Creates and returns the CR api from streamlink
        """
        session = Streamlink()
        session.set_loglevel("debug")
        plugin = session.get_plugins()['crunchyroll']('')
        plugin.options.set('username', username)
        plugin.options.set('password', password)
        return plugin._create_api()

    def __init__(self, username: str, password: str) -> None:
        self._api = CrunchyrollAPI._create_api(username, password)
        self._search_candidates: Optional[list] = None

    def list_series(self,
                    media_type: MediaType,
                    search_filter: Filters,
                    search_filter_param: Optional[str] = None,
                    limit: Optional[int] = None,
                    offset: Optional[int] = None) -> list:
        """ Returns a list of series given filter constraints
        """
        params: Dict[str, Any] = {
            "media_type": media_type,
            "filter": search_filter.value + (search_filter_param if search_filter_param else ""),
        }

        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self._api._api_call("list_series", params)

    def list_collections(self,
                         series_id: str,
                         sort: Optional[SortOption] = None,
                         limit: Optional[int] = None,
                         offset: Optional[int] = None) -> list:
        """ Returns a list of collections for a given series
        """
        params: Dict[str, Any] = {
            "series_id": series_id,
        }

        if sort:
            params["sort"] = sort.value
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self._api._api_call("list_collections", params)

    def list_media(self,
                   series_id: str,
                   sort: Optional[SortOption] = None,
                   limit: Optional[int] = None,
                   offset: Optional[int] = None,
                   locale: Optional[Any] = None) -> list:
        """ Returns a list of media for a given series
        """
        params: Dict[str, Any] = {
            "series_id": series_id,
        }

        if sort:
            params["sort"] = sort.value
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if locale:
            params["locale"] = locale

        return self._api._api_call("list_media", params)

    def list_search_candidates(self) -> list:
        """ Returns a list of search candidates (Series)
        """
        res = requests.get(CR_AJAX_ANIME_LIST)
        data = json.loads(res.text[len('/*-secure-'):-len('*/')])['data']
        series = [elt for elt in data if elt['type'] == 'Series']
        return series

    def get_queue(self, media_types: MediaType, fields: Optional[List[str]] = None):
        """ Return queue
        """
        params: Dict[str, Any] = {
            "media_types": media_types,
        }

        if fields:
            params["fields"] = fields

        return self._api._api_call("queue", params)

    def search(self, search_term: str) -> List[str]:
        """ Search anime """
        results = []
        if self._search_candidates is None:
            self._search_candidates = self.list_search_candidates()

        search_term = search_term.lower()
        for series in self._search_candidates:
            if search_term in series['name'].lower():
                results.append(series)

        return results

    def remove_from_queue(self, series_id: str):
        """ Delete series from queue """
        params = {
            "series_id": series_id
        }
        return self._api._api_call("remove_from_queue", params)
