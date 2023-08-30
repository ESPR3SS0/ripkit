


# First model 
Feed whole files, so the saved anaylsis was binary one hot encoded 
with func_[start|end|middle] labels 


# New model 
Feed blocks of bytes, labelling a whole block as start or not 


[0xnn, ...] YES is a function start 

slide the window...

[0xtt, ...] NO is not a function start



# In these two cases, different analysis forms of the files are needed. 

Current Implementation:
Save a compressed numpy array with the vector specified in First model 

Current speed issues:
    - Analysis per binary takes the longest time 
    - Loaded the binaries into memory takes a long time 


New Implementation troubles:
    - Requires re-analysis of files 

# New Implementation ideas

1. Follow my initial dream of storing a large file with information 
about each binary, then at run time pull the information that I want 
from the files 

2. Re-analyze files but this time only save the byte, and function start 
or end labels

For the sake of the project I will have to sacrifice my dream in favor 
of the simpiler number 2.... but while I'm thinking about it....


# Binary file domintation 
I wanted to have a database with a pandas table that held 
every byte in a file, func_[start,end,middle], function length,
function name and more. This way I could have a super slick 
cli app that allows fast analysis of files.

Relisticly this wasn't useful besides being fast and flexible
for data pre processing. But the files were too large. 

What both of my models have needed so for is a list of bytes, 
and whether or not that byte is a start or end of function.

The lief objects are powerful. I could save the pickled lief 
object with the file, then write a script that provides 
generators for various needed data things.

For a model, I'd rather have this data cache (or saved), meaning 
I don't have to generate the data every training session but 
instead just have to read it. 

But what I could do is generate it once, then cache it for the 
remaining epochs. This doesn't have my slick cli tool as much, 
but would help model training


