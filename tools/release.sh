#!/bin/sh

# Run this from the root directory of Luminotes's source.

cd ..
rm -f luminotes.tar.gz
tar cvfz luminotes.tar.gz --exclude="session/*" --exclude="*.log" --exclude="*.pyc" --exclude=".*" luminotes
cd -
