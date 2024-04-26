# adulting

Scripts to help me organise my day to day life.

# Installation

You can put any or all the scripts in a directory that is in your system's executable path. I have a `bin` directory in my working directory and clone the repo into that. 

So - 

```
cd ~
mkdir bin
cd bin
git clone git@github.com:riazarbi/adulting.git
```

Then add...

```
export PATH=/Users/riaz/bin:$PATH
```

...to the bottom of your `.zshrc` or `.bashrc` file.

# Scripts

## networker

Helps you keep track of interactions with people in your network. Reminds you when you haven't interacted with someone for too long.  

If it's in your `PATH`, call it by typing `networker` in your terminal. This will present you with a menu like so:

```
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




# Design goals

Each script should:

- Run on MacOS or Linux (the shebangs might not play nice).  
- One self contained file per utility.  
- Require no additional libraries over and above base system libraries.  
- Be operated from the command line.
- Maintain state in simple text-based file formats.
- Maintain all state in an `.adulting` hidden directory in the users home directory.