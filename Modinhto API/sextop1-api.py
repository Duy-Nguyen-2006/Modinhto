#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="sextop1",
    search_func_name="search_videos_by_actor",
    title="SexTop1 crawler API",
    default_port=8005,
)

if __name__ == "__main__":
    main()
