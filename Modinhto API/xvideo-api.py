#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="xvideo",
    search_func_name="search_videos_by_actor",
    title="XVideos crawler API",
    default_port=8009,
)

if __name__ == "__main__":
    main()
