# Getting Started

ColorHelper is designed to do the following:

- Show inline previews in supported files.
    ![inline](res://Packages/ColorHelper/docs/images/inline_previews.png){: width=268px, height=102px }

- Provide helpful panels that allow you to:
    - Convert color form.

        ![inline](res://Packages/ColorHelper/docs/images/color_info.png){: width=259px, height=281px }

    - Insert colors from saved color palettes or from the current file's color palette.

        ![inline](res://Packages/ColorHelper/docs/images/palettes.png){: width=315px, height=269px }

    - Access a limited native color picker or a more native color picker via the  
    [ColorPicker plugin](http://facelessuser.github.io/ColorHelper/usage/#enable_color_picker).

        ![inline](res://Packages/ColorHelper/docs/images/alternate_color_picker.png){: width=493px, height=534px }

Color previews should dynamically appear in supported files.  They are loaded as needed, so you will see them appear  
as you scroll.

Popup panels will appear when your cursor is on a color or when you click a color preview, you can disable both  
features if you like.

For more information on using and configuring the panels, check out the [documentation](http://facelessuser.github.io/ColorHelper/usage/).

# ColorHelper Doesn't Support My Sass or SCSS Variables

That is true.  There are no current plans to support this, but maybe in the future.

# ColorHelper Doesn't Support my CSS, Sass, or SCSS File.

You probably are using a syntax highlighter file that hasn't had support added yet.  A pull request may be required.

# ColorHelper Doesn't Support Colors in (Insert File Type Here)

You may need to add support rules via a pull request.  Check out the [settings](sub://Packages/ColorHelper/color_helper.sublime-settings) file to see existing rules.

# ColorHelper Doesn't Support My Custom Colors Format

ColorHelper currently supports CSS3 style colors and probably most CSS4 colors (if enabled).  Some rework is planned  
to allow more flexible ways to define custom colors, but that work has not been completed yet.

# I Need Help!

That's okay.  Bugs are sometimes introduced or discovered in existing code.  Sometimes the documentation isn't clear.  
Support can be found over on the [official repo](https://github.com/facelessuser/ColorHelper/issues).  Make sure to first search the documentation and previous issues  
before opening a new issue.  And when creating a new issue, make sure to fill in the provided issue template.  Please  
be courteous and kind in your interactions.
