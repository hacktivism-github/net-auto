# Use Case No. 1

### Overview
This python script was built by putting together small portions of code available at the "[Junos PyEZ Developer Guide](https://www.juniper.net/documentation/en_US/junos-pyez/information-products/pathway-pages/junos-pyez-developer-guide.html)" with the intent to maintain a Git repository for configuration management always current ("source of truth"), while providing the Network Engineers distributed across different timezones informed, with the benefit to easily co-relate events and/or incidents to changes (to begin with), thus making troubleshooting smoother.

![Example No.1 Diagram](/images/ex-no1.png)

### Workflow
* The script is set to run from a cron job call on a specific frequency.
* A NETCONF session over SSH is established to all nodes in the .yml file sequentially.
* A get_config() Remote Procedure Call (RPC) is executed to request the complete configuration.
* On receiving the config it opens/creates a file (for each node) to write the data (ASCII for now) and names it after the entry on the .yml file for which it's performing the RPC for, and makes it a .txt on closing the file and before moving to the next node on the list. 
* Upon completion (gathering config data) the script runs git add --all to  add them all to the repo, then commit and push.

Happy Labbing!

/me
