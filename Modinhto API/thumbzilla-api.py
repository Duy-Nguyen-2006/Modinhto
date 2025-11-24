#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="thumbzilla",
    search_func_name="search_videos_by_actor",
    title="Thumbzilla crawler API",
    default_port=8006,
)

if __name__ == "__main__":
    main()
