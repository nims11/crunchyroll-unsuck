""" Extending crunchyroll api implemented in streamlink
"""
import json
from .config import USER, PASS
from streamlink.session import Streamlink


class CrunchyrollAPI(object):
    def __init__(self):
        self.session = Streamlink()
        self.session.set_loglevel("debug")
        self.plugin = self.session.get_plugins()['crunchyroll']('')
        self.plugin.options.set('username', USER)
        self.plugin.options.set('password', PASS)
        self.api = self.plugin._create_api()
        self.search_candidates = None


    def list_series(self, media_type, filter, limit=None, offset=None):
        """ Returns a list of series given filter constraints
        """
        params = {
            "media_type": media_type,
            "filter": filter,
        }

        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self.api._api_call("list_series", params)


    def list_collections(self, series_id, sort=None, limit=None, offset=None):
        """ Returns a list of collections for a given series
        """
        params = {
            "series_id": series_id,
        }

        if sort:
            params["sort"] = sort
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self.api._api_call("list_collections", params)


    def list_media(self, series_id, sort=None, limit=None, offset=None, locale=None):
        """ Returns a list of media for a given series
        """
        params = {
            "series_id": series_id,
        }

        if sort:
            params["sort"] = sort
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if locale:
            params["locale"] = locale

        return self.api._api_call("list_media", params)


    def list_search_candidates(self):
        """ Returns a list of search candidates (Series)
        """
        res = self.session.http.get('http://www.crunchyroll.com/ajax/?req=RpcApiSearch_GetSearchCandidates')
        data = json.loads(res.text[len('/*-secure-'):-len('*/')])['data']
        series = [elt for elt in data if elt['type'] == 'Series']
        return series


    def get_queue(self, media_types, fields=None):
        """ Return queue
        """
        params = {
            "media_types": media_types,
        }

        if fields:
            params["fields"] = fields

        return self.api._api_call("queue", params)


    def search(self, search_term):
        results = []
        if self.search_candidates == None:
            self.search_candidates = self.list_search_candidates()

        search_term = search_term.lower()
        for series in self.search_candidates:
            if search_term in series['name'].lower():
                results.append(series)

        return results
