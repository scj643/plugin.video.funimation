from resources.lib.controllers.base_controller import BaseController
from resources.lib.models.trailer import Trailer


class TrailersController(BaseController):
    def __init__(self, node, show_id=None, page='0'):
        super(TrailersController, self).__init__()
        self.json = node
        self._common.log(node)
        self.page = int(page)
        self.show_id = show_id

        if isinstance(self.json, dict):
            get = self.json.get
            if get('node') > 0:
                for attr in get('node'):
                    self._common.log(attr, 9)
                    self._items.append(Trailer(attr['show']))

    def itemize(self):
        return [ep.itemize() for ep in self]