#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="mupvl",
    search_func_name="search_videos_by_actress",
    title="MupVL crawler API",
    default_port=8010,
)

if __name__ == "__main__":
    main()
