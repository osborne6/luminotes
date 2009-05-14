#!/bin/sh

montage -tile x1 -geometry 40x40 -background none static/images/toolbar/*_button.xcf static/images/toolbar/buttons.png
montage -tile x1 -geometry 20x20 -background none static/images/toolbar/small/*_button.xcf static/images/toolbar/small/buttons.png
