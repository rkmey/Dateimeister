[33m436a6e3[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mmaster[m[33m)[m Diatisch_support: conversion to class cont.
[33m4b8c5c6[m[33m ([m[1;31morigin/master[m[33m)[m Diatisch_support: conversion to class cont.
[33m0246947[m Diatisch_support: conversion to class cont.
[33m219563b[m Diatisch_support: conversion to class cont.
[33mfa87f3c[m Diatisch_support: conversion to class cont.
[33m9cb792e[m  Diatisch_support: conversion to class cont.
[33mb93074c[m Diatisch_support: conversion to class cont.
[33m38df148[m Diatisch_support: conversion to class cont.
[33m7430c29[m Diatisch_support: conversion to class cont.
[33m4b61670[m Diatisch_support: conversion to class cont.
[33mc71d3a6[m Diatisch_support: conversion to class cont.
[33m4820043[m Diatisch_support: conversion to class cont.
[33me9b7e57[m Dateimeister_support: conversion to class continued
[33m98ab220[m new class Dateimeister_support, begin of conversion to object oriented
[33m0a44114[m Diatisch: new dict filename (source) image allows to have images only once for source and target as targe is a subset of source. Key is filename. Images are no mpre stored in myImage objects, just the filenames
[33m0fbb122[m Diatisch: expand some undo / redo- prints, use methods for getting filename / image instead of direct accessing attributes
[33m8f17897[m Distisch: restore select counter when undo / redo
[33mc786a20[m Diatisch: set single image to delete to None after delete action
[33m984a993[m Diatisch: restore select status after delete action (same problem as before with copying), use filename of single image to delete for comparison instead of image in unequal-condition
[33m6f7f963[m  Diatisch: correct false selection after undo / redo (continued)
[33m3077356[m Diatisch: correct false selection after undo (started, to be continued)
[33mb222490[m Diatisch: make callable from Tools menue of Dateimeister, Dateimeister: rename Camera menue -> Tools, add menuitem Diatisch
[33m9762243[m implement Diatisch undo / redo logic in Dateimeister and Dateimeister/Camera
[33mdc8a6cd[m Diatisch: rdesign undo / redo introducing stack_processids for undoing and redoing
[33mea0051b[m added hashsums for image filenames and image selection to historized objects for choosinf necessary actions after undo / redo"
[33m5b37cb3[m historize target canvas only if it has changed(lsit of old / new filenames not identical)
[33m13efac4[m Diatisch: solved an issue that after target canvas rebuild all item show selection frame independent of selected attribute. This i because items are rebuild and the frame comes last, so it is on top. Therefore the unselect method no more checks if select attribute is gt 0
[33m29bb5c0[m Diatisch: fixed problem of duplicate images after drag in target canvas wnn drop position outside all images
[33ma054745[m Diatisch: new method select shows which shows only frame but does not change select-counter, used in undo / redo
[33m6a17b25[m exclude sln-File
[33m9b63d64[m Merge branch 'master' of https://github.com/rkmey/Dateimeister
[33m44d7db8[m consolidate .gitignore
[33m908a55c[m exclude VisualStudio directory and project file from git
[33mbb30048[m Diatisch: class variable for line width
[33m9c5e309[m Diatisch: class variable for line width of select frame for images
[33m1945992[m Diatisch: fix a problem with exceptions when displaying filename as tooltip
[33m3dea091[m Diatisch: Delete target images first implementation
[33mb7eedd7[m Diatisch: Functions for delete selected / single implemented
[33mba8627b[m Diatisch: uncomment some unnecessary print
[33m7adddd1[m Diatisch: no historize if action in target and drop outside images
[33mb80d6c1[m Merge branch 'master' of https://github.com/rkmey/Dateimeister
[33m34a8208[m consolidate
[33m291bd61[m Diatisch: copy single source image from context menu, without checking if selected etc.
[33mae14472[m Diatisch: canvas ids for select-rect replaced by string Pnn because ids change when rebuilding canvas
[33meb95a52[m Diatisch: undo/redo use copies of original image objects
[33mb63e40f[m diatisch: undo/redo of select / unselect
[33m544efcb[m Diatisch: undo redo functions first implementation cont.
[33m1522514[m Diatisch: undo redo functions first implementation
[33m74968e7[m Diatisch: Undo / Redo buttons
[33m4103da3[m Diatisch context menu copy selected
[33mab97e71[m Diatisch: Button copy selected, functionality implemented
[33mf016a91[m Diatisch: copy selected cont.
[33m1005b4c[m Diatisch: do selection after update target canvas because frameids are not correct before update
[33md1e99cf[m Diatisch: use same function (display_image_objects) to build / update canvasses
[33mef04df5[m Diatisch fix select problem in target canvas
[33m57d6606[m Diatisch source copy selected button
[33m0e29469[m Diatisch Select all source images Button and Function
[33m51c7ecb[m Diatisch dekete button
[33m945c943[m Diatisch select dragged images on target, unselect all others, skip dragged images already existing in target
[33m018bf97[m Diatisch append dragged files at the end if no image is hit on drop
[33mdc1840a[m Diatisch drag and drop withhin target cont.
[33ma89db0c[m Diatisch sort target images
[33m13c6eb6[m Diatisch Selection Corrections
[33me18add2[m Diatische select / unselect revisited
[33mda0cdf2[m Diatisch Doc
[33m6b9ac6f[m Diatisch decision table
[33ma227bc5[m Diatisch drag and drop within target
[33m72b6042[m  Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet, fix select problem on target canvas
[33m34dec65[m  Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet, context menu and tooltip.filename
[33mada11a7[m  Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet
[33me029cb5[m Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet
[33m1a13339[m Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet
[33m9f8da29[m Diatisch application (drag / drop) continued, move within target canvas implemented, not working yet
[33m69d5ee3[m Diatisch application (drag / drop) continued, list_dragged_images is no more an instance variable
[33mff11fe6[m Diatisch application (drag / drop) continued
[33m589ec86[m Documentation of control states, cont., select in own function
[33m2b1fd93[m Documentation of control states, cont. insert at correct position
[33m57fe77d[m Documentation of control states, cont.
[33m049baf3[m Documentation of control states, cont.
[33m082f6bc[m Documentation of control states, cont.
[33m379aae7[m  Documentation of control states, cont.
[33ma560d13[m Documentation of control states, cont.
[33m3538fbe[m Documentation of control states, cont.
[33mb083403[m Documentation of control states, cont.
[33mf709073[m Diatisch application (drag / drop) continued
[33m6bb79b4[m Diatisch application (drag / drop) continued
[33mcc330c0[m Diatisch application (drag / drop) continued
[33m732e638[m  Diatisch application (drag / drop) continued
[33m5c3df62[m Diatisch application (drag / drop) continued
[33m029fdd4[m Diatisch application (drag / drop) begun
[33m0d62fab[m Documentation of control states, cont.
[33m390cf66[m Documentation of control states, cont.
[33mc80a99c[m Documentation of control states, started
[33m0c865c7[m text widget double click and canvas return key bring up FSImage
[33m52a5254[m text widget: use bindtags to enforce correct sequence of event handlers, set cursor after up / down to col 1
[33m875aa92[m text widget, add arrow up / down event
[33m6475dbf[m solved issue #19: scroll does not work for not displayable image
[33mc2c787a[m frame in canvas gallery for selected image
[33m3c9f6ff[m[33m ([m[1;33mtag: [m[1;33mv.1.0.2[m[33m)[m undo/redo in main and vamera window: simplify to just apply last / next process_status in undo / redo, removes some strange behavior
[33m5adcb2e[m fixed some doumentation errors
[33mec9b30e[m fixed an error closing FSImage from duplicates twice by setting _win_duplicates to None in duplicates own close method, scroll to start of canvas (main window) after browse / edit
[33mbcd096e[m[33m ([m[1;33mtag: [m[1;33mv.1.0.1[m[33m)[m main window: added scrollbar to listbox camera, updated page to version 8.0
[33m9ac3cb2[m main window: scrollbars for text do not overlap text anymore. attached to new frame1. issue #17
[33m1a5e85a[m updated todo for immediate visibility of new config file in recent menu
[33md627327[m git docu
[33m8c56e89[m corrected comment in text1_double
[33m1cc8942[m main window: highlight line in textbox when double clicked
[33m38b71ce[m[33m ([m[1;33mtag: [m[1;33mv1.0.0[m[33m)[m camera window: ctrl-z and ctrl-y added for undo / redo
[33me492a9c[m camera window: undo / redo implemented
[33mc289135[m camera window: add historize function, change some variables from global to instance variables
[33m1f9ec27[m camera window : minor changes in layout
[33m3b03aa6[m camera window: undo / redo started, changes required
[33mfddb141[m ToDo: requirements written on paper included
[33m8e5ae16[m consolidation of anforderungen.zxz and todo.txt in dateimeister-todo.txt
[33m775007c[m ToDo-list
[33m358fceb[m function close_child_windows for closing all child windows, dicts for duplicates moved from global to duplicates class, error corrections
[33m792fefe[m camera window: added todo comment to what has to be done after apply_new
[33mf9458ec[m camera window: when changes applied, refresh dicts and call state_gen_required for main window
[33m1f92b17[m camera window: added dialogs for camera, new,...
[33m3344497[m camera window: new cancel button, enable_processing: simplify, fill all entries
[33m960b5f0[m camera window: lock / unlock treeview depending on transaction state, change backgrond colour to grey if locked
[33m9483434[m camera window: set text (e.g. Camera) in disabled entry
[33m5baa997[m camera window: when new type selected force entry for type-suffix
[33ma90f622[m camera window: 3 new entries / labels, not fully functioning yet
[33md3df07b[m camera window delete all context menu items when selected
[33m6da777d[m new type / subdir in camera window and dateimeister_config.xml
[33m43aef11[m close messages window after Button browse / edit, disable apply button, return key in camera window when not menuitem selected
[33m9da92b6[m added proccessing_type to suffix-context-menu, processing-types moved from xnl to ini-file because they spend upon program code
[33m6aec458[m camera dialog: check suffix after all cameras have been processed in treeview_from_xml
[33m23dd6fc[m camera dialog change type, delete type, message if new type has no suffix, show new suffix dialog
[33mae80442[m camera dialog: suffix delete, type new
[33m17f267d[m Suffix always in uppercase when selected from text entry
[33mf89b722[m Refresh treeview after new, change,.., change suffixname, new columns for subdir, process
[33m28a802b[m expand camera node after new suffix - not yet working
[33mb1d44b1[m insert new suffix in cameratype, asking for suffix-name
[33m661b2e1[m camera context menu: create menuitems dependent on item tag in treeview
[33m8c5e01e[m camera context menus fixed button 3 show, position
[33mdc1bd7f[m context-menu initial, position is still wrong and false reaction to mouse buttons
[33mbe27ea2[m new function get_cameras_usedate, get treeview selection, treeview mode browse etc.
[33m716ba45[m initialize camera treeview from xml
[33m420ee35[m mini docu for pyinstaller
[33mb11a33a[m added treeview window for camera dialog
[33mc33f378[m Docu _make-exe.txt not in git
[33med63832[m exclude dirs generated by pyinstaller
[33mf313b73[m enable / disable Checkbutton MyMessagesWindow.delrelpath, new lable for scripttype in MyMessagesWindow
[33m2c63e6a[m getState: autosave except for mass calls, here it is done manually by invoking write_cmdfile, save button removed
[33m4a0368a[m copy / delete moved from main window to Messages Window
[33m848f237[m copy / delete moved to MyMessagesWindow
[33m7eed79b[m cmd-messages, errors from copy in MyMessagesWindow separate textboxes
[33mb684da8[m Messages-Window with scrollbars
[33mb742251[m gitignore um tcl erweitert
[33m56a7f88[m backup-Datei wird nicht benoetigt
[33m2e44f9c[m new camera dialog, fix delete thumbnails after checkboxes state changed
[33m78b841a[m disable / enable GUI elements after changing camera or state of checkbuttons
[33m3af17e8[m Konfigurationsdateien gehoeren in config bzw. datadir/config
[33m87fbb90[m pycache in gitignore
[33m8a59d35[m __pycache__ in gitignore
[33m9461aa4[m Fehlerbehebung askopenfile initialdir aus Versehen geloescht
[33m50e1904[m added comment referring to strange behavior of os.path.join
[33m2cf238a[m test ini gitignore
[33me1d447d[m Trennung generierte Daten Code im Repository durch Einfuehrung datadir
[33m949cca9[m generierte jpeg-Dateien loeschen
[33mb08429b[m Laufwerk auf E: geaendert
[33m32c8e7f[m camera window class added
[33m05fa557[m[33m ([m[1;31morigin/main[m[33m)[m Add files via upload
[33m0553156[m Add files via upload
[33mf41cce5[m Update README.md
[33m07e8233[m Initial commit
