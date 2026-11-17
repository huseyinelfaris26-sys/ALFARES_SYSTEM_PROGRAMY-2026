# Local development/laptop installation
python -m pip install -e '.[api,postgres,test]'

# Optional machine-learning stack; install only when needed
python -m pip install -e '.[ml]'

# Optional geospatial tooling; rasterio/GDAL may need platform-specific setup on Termux
python -m pip install -e '.[geo]'
