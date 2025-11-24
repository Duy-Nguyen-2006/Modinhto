#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="xhamster",
    search_func_name="search_videos_by_actor",
    title="XHamster crawler API",
    default_port=8008,
)

if __name__ == "__main__":
    main()
