# adulting

Scripts to help me organise my day to day life.

# Installation

You can put any or all the scripts in a directory that is in your system's executable path. I have a `bin` directory in my working directory and clone the repo into that. 

So - 

```zsh
cd ~
mkdir bin
cd bin
git clone git@github.com:riazarbi/adulting.git
```

Then add...

```zsh
export PATH=/Users/riaz/bin/adulting:$PATH
```

...to the bottom of your `.zshrc` or `.bashrc` file.

# Scripts

## networker

Helps you keep track of interactions with people in your network. Reminds you when you haven't interacted with someone for too long.  

If it's in your `PATH`, call it by typing `networker` in your terminal. This will present you with a menu like so:

```zsh
No overdue interactions found.

Hit [ENTER] to log an interaction or select from the options below:
1.      Add Contact
2.      Update Time Bucket
3.      View Contact
4.      Overdue Interactions
5.      List All Contacts
6.      Log Interaction
7.      Exit
```

Overdue interactions will appear at the top of the menu, or can be listed by selection the appropriate option. 

You can also skip the menu by passing the menu option as an argument, like `networker 1` for instance.

These are the basic operations:

`Add Contact` - add a name and a desired catch-up cadence  
`Update Time Bucket` - change the desired frequency of interaction with someone  
`View Contact` - get infor about a ocntact, as well as a list of recent interactions  
`List All Contacts` - list all contacts  
`Log Interaction` - log an interaction with a contact  

Want to delete a contact? Just set their time bucket to `adhoc`.

Data is stored in csv format in the `.adulting` hidden directory. You can use these files for data analysis if you want to get elaborate.


## threads

I often struggle to keep track of all the projects I am involved in. Sometimes I'll forget that I've started something and only rediscover it when I get an angry email from someone who was waiting for the finished product! This utility helps me keep a record of all my open threads, and helps refresh my memory on the status of each thread. 

What is a thread? Anything, really. 'Beetle Restoration', 'JIRA-1234', 'PTA Bake Sale' or whatever else you care about. Each thread is saved in its own file in `.adulting/threads/`. 

If this file is in your `PATH`, call it by typing `threads` in your terminal.

When you invoke `threads`, it will read in the data from the various threads files and work through each thread one after the other. For each thread, you'll get a printout of the last few logs that you made against that thread, and you will be provided with a prompt to add a new log. You can also just hit [Enter] to skip or type CLOSED to remove the thread from your regular review cycle. I try to run threads once a day, at the end of the day. The main review cycle looks something like this:

```zsh
###================ THREAD LOGGER ================###

These are the current threads ==>
PTA Bake Sale

Working through threads...

-----------------------------------------------------

THREAD  ===>  PTA  BAKE  SALE

2024-04-26    test

Enter a new log:
  press [Enter] to skip...
  type CLOSED to close the thread...

Skipping...

=====================================================

Would you like to create a new thread [y/N]? 
```

There are also several reports you can generate:

- `threads --report` summarises all the activity by thread for the last week.  
- `threads --daily YYYY-MM-DD` gives you the activities you completed on a particular day. This is good for time tracking!
- `threads --tail` gives you the last reported activity for each open thread. This is nice for a concise overview of where you are with everything going on in your life.

```zsh
riaz@Riazs-MacBook-Pro % threads --tail
THREAD  ===>  PTA  BAKE  SALE
2024-04-26    test
-----------------------------------------------------
THREAD  ===>  SGB
2024-04-26    Still waiting for my email address.
-----------------------------------------------------
```

## notes

This is my really simple note taker. It's just a single bash script, and it saves all notes to `~/.adulting/notes`. If it's in your `PATH`, call it by typing `notes` in your terminal. It relies on `nano` as the text editor, but there's no reason you can't swap it out for something else. 

There are six basic operations:

1. `--new` will take you through a dialog to create a new note. It'sll ask you what type of note it is, what thread it relates to (see `threads` above), the topic of the note etc. Then it'll open up a prepopulated note in your text editor, which you can fill out, and save. 
2. `--edit` will present you with a list of all your notes, ordered by time, and ask you which one you want to edit, and then open it up for you.
3. `--delete` will present you with a list fo notes and ask you which one you want to delete and then delete it.
4. `--last` will open the last note.
5. `--read` will open a note in read mode in a pretty format. [actually this is currently broken]
6. `--actions` will scan all your notes for markdown-formatted task list items that are open (`- [ ] ...`) and present them in a single text editor panel. You can edit them (mark them closed etc) and, when you save and close the editor, all the action items will be changed in the source notes files.

If you just type `notes`, with no argument, you'll automatically be sent through the `--new` workflow.

## summary

A utility to print a summary of your various adulting utilities. If it's in your `PATH`, call it by typing `summary` in your terminal.

If you want to print a summary every time you open a terminal, add `summary` to the bottom of your `.bashrc` or `.zshrc` file.


# Design goals

Each script should:

- Run on MacOS or Linux (the shebangs might not play nice).  
- One self contained file per utility.  
- Require no additional libraries over and above base system libraries.  
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state in an `.adulting` hidden directory in the users home directory.