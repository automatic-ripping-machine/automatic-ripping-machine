## For v2.4 or newer

ARM makes use of [Bootstrap](https://getbootstrap.com) for alot of the heavy lifting with the ARM ui. One of the benefits of using this is that it allows users to easily customise all of the ARM ui thanks to themes/skins for bootstrap.

You can get great selection of skins/Themes from here [bootswatch](https://bootswatch.com)

The process for updating the Skin/Theme is pretty simple
   - Find the Theme you like
   - Download its bootstrap.min.css file
   - Place the file inside (arm install path)/arm/ui/static/css
   - You should overwrite the previous file
   - Clear your browser cache (Shift + F5 on some browsers CTRL + F5 on others)
   - Thats it!


The default path for ARM unless you have changed it is `/opt/arm/`
This would mean the default full path for the bootsrap.min.css file would be `/opt/arm/arm/ui/static/css/bootstrap.min.css`

## For versions older than v2.4

Follow the above steps, there is an additional step that is required

 - You will need to change the downloaded file name to bootstrap.spacelab.css and then copy it to the above directory. The only difference being that the final full path would be ``/opt/arm/arm/ui/static/css/bootstrap.spacelab.css``
