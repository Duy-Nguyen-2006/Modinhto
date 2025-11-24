#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from api_shared import create_api

app, main = create_api(
    module_name="vailonxx",
    search_func_name="search_videos_by_actor",
    title="Vailonxx crawler API",
    default_port=8007,
)

if __name__ == "__main__":
    main()
