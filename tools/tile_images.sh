#!/bin/sh

montage -tile x1 -geometry 40x40 -background none static/images/toolbar/*_button.xcf static/images/toolbar/buttons.png
montage -tile x1 -geometry 20x20 -background none static/images/toolbar/small/*_button.xcf static/images/toolbar/small/buttons.png

for theme_dir in static/images/toolbar/themes/* ; do
  montage -tile x1 -geometry 40x40 -background none $theme_dir/*.xcf $theme_dir/buttons.png
  montage -tile x1 -geometry 20x20 -background none $theme_dir/small/*.xcf $theme_dir/small/buttons.png
done
