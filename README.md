**See below for [screenshots](#screenshots)**

***

world2minetest is a tool to generate [Minetest](https://www.minetest.net/) worlds based on publicly available real-world geodata. It was inspired by tools such as [geo-mapgen](https://github.com/Gael-de-Sailly/geo-mapgen).

Currently, the following geodata sources are supported. Heightmaps and .dxf CAD files must use the [EPSG:25832](https://epsg.io/25832) coordinate system.
 * Heightmaps in "XYZ ASCII" format
 * [OpenStreetMap](https://openstreetmap.org), using the [Overpass API](https://overpass-turbo.eu/)
 * .dxf CAD files (trees & bushes only)



Installation
============

 1. Copy this repo's content to your computer, e.g. by cloning:
    ```
    git clone https://github.com/FlorianRaediker/world2minetest.git
    ```
 2. Install the required Python modules:
    ```
    pip3 install -r requirements.txt
    ```



How to use
==========

We offer a [simple guide](SimpleGuide.md) to easy world generation based solely on a apir of coordinates and using only openstreetmap data.

We also offer a [detailed guide](DetailedGuide.md) including the use of heightmaps, openstreetmap data, decorations as well as 3-D data.


License
=======
world2minetest - Generate Minetest worlds based on real-world geodata<br>
Copyright (C) 2021-2022  Florian Rädiker

This program is free software: you can redistribute it and/or modify<br>
it under the terms of the GNU Affero General Public License as published<br>
by the Free Software Foundation, either version 3 of the License, or<br>
(at your option) any later version.

This program is distributed in the hope that it will be useful,<br>
but WITHOUT ANY WARRANTY; without even the implied warranty of<br>
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the<br>
GNU Affero General Public License for more details.<br>

You should have received a copy of the GNU Affero General Public License<br>
along with this program.  If not, see <https://www.gnu.org/licenses/>.
