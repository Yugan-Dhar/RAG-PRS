import json
import os

data = {
  "standard": {
    "id": "ITSAR_ROUTER",
    "name": "ITSAR IP Router",
    "version": "2.0.0",
    "document_number": "ITSAR201012512",
    "date": "2025-12-01",
    "issuer": "NCCS, Department of Telecommunications, India"
  },
  "router_types": [
    "conventional", "sdn", "cloud_native", "virtual", "cloud_managed"
  ],
  "sections": [
    {
      "id": "2.1",
      "title": "Access and Authorization",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.1.1",
          "title": "Authentication for Product Management and Maintenance interfaces",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "evidence_type": "technical",
          "is_prohibition": False,
          "compliance_by_undertaking": False,
          "text": "IP Router shall support mutual authentication of entities on management interfaces. The authentication mechanism can rely on the management protocols used for the interface or other means. Secure cryptographic controls prescribed in Table 1 of the latest document 'Indian Telecommunication Security Assurance Requirements (ITSAR) for Cryptographic Controls' shall only be used for IP Router management and maintenance.",
          "keywords": ["mutual authentication", "management interfaces", "cryptographic controls"],
          "cross_references": ["ITSAR_CRYPTO:Table1"]
        },
        {
          "id": "2.1.2",
          "title": "Management Traffic Protection",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "IP Router management traffic (information exchanged during interactions with OAM) shall be protected strictly using secure cryptographic controls prescribed in Table 1 of the latest document 'Indian Telecommunication Security Assurance Requirements (ITSAR) for Cryptographic Controls' only.",
          "keywords": ["management traffic", "OAM", "protected", "cryptographic controls"],
          "cross_references": ["ITSAR_CRYPTO:Table1"]
        },
        {
          "id": "2.1.3",
          "title": "Role-Based access control policy",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The IP Router shall support Role Based Access Control (RBAC). A role-based access control system shall use a set of controls which determines how users interact with domains and resources. The domains could be Fault Management (FM), Performance Management (PM), System Admin, etc. The RBAC system shall control how users or groups of users are allowed access to the various domains and what type of operation they can perform, i.e. the specific operation command or command group (e.g. View, Modify, Execute).",
          "keywords": ["Role Based Access Control", "RBAC", "user roles", "OAM privilege management"],
          "sub_requirements": [
            {
              "id": "2.1.3.a",
              "text": "The IP Router shall support RBAC with minimum of 3 user roles, in particular, for OAM privilege management for network product Management and Maintenance, including authorization of the operation for configuration data and software via the network product console interface.",
              "obligation": "SHALL"
            },
            {
              "id": "2.1.3.b",
              "text": "The RBAC shall be applicable to API users also.",
              "obligation": "SHALL"
            }
          ]
        },
        {
          "id": "2.1.4",
          "title": "User Authentication – Local/Remote",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The various user and machine accounts on a system shall be protected from misuse. To this end, an authentication attribute shall be used, which, when combined with the username, shall enable unambiguous authentication and identification of the authorized user. Authentication attributes include: Cryptographic keys, Token, Passwords.",
          "keywords": ["authentication attribute", "unambiguous authentication", "cryptographic keys", "token", "passwords"],
          "sub_requirements": [
            {
              "id": "2.1.4.a",
              "text": "Minimum two of the above Authentication attributes shall be mandatorily combined for protecting all the accounts from misuse. An exception to this requirement is local access and machine accounts where at least one authentication attribute shall be supported",
              "obligation": "SHALL"
            }
          ]
        },
        {
          "id": "2.1.5",
          "title": "Remote login restrictions for privileged users",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "Direct Login to IP Routers as root or equivalent highest privileged user shall be limited to the system console only. Root user shall not be allowed to login to IP Router remotely. This remote root user access restriction is also applicable to application software’s / tools such as TeamViewer, desktop sharing which provide remote access to the IP Router.",
          "keywords": ["root", "highest privileged user", "system console only", "not be allowed to login to IP Router remotely"]
        },
        {
          "id": "2.1.6",
          "title": "Authorization Policy",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The authorizations for accounts and applications shall be reduced to the minimum required for the tasks they have to perform. Authorizations to IP Router shall be restricted to a level in which a user can only access data and use functions that he needs in the course of his work.",
          "keywords": ["minimum required", "restricted to a level"]
        },
        {
          "id": "2.1.7",
          "title": "Unambiguous identification of the user & group accounts removal",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "Users shall be identified unambiguously by the IP Router. IP Router shall support the assignment of individual accounts per user. IP Router shall not enable the use of group accounts or group credentials, or sharing of the same account between several users.",
          "keywords": ["identified unambiguously", "individual accounts per user", "not enable the use of group accounts"]
        }
      ]
    },
    {
      "id": "2.2",
      "title": "Authentication Attribute Management",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.2.1",
          "title": "Authentication Policy",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The usage of a system function without successful authentication, on the basis of the user identity and at least two authentication attributes shall be prevented. For machine accounts and local access one authentication attribute will be sufficient.",
          "keywords": ["successful authentication", "two authentication attributes"]
        },
        {
          "id": "2.2.2",
          "title": "Authentication Support – External",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "If the IP Router supports external authentication mechanism such as AAA server, then the communication between IP Router and the external authentication entity shall be protected using the authentication and related service protocols built strictly using the Secure cryptographic controls prescribed in Table 1 of the latest document “ITSAR for Cryptographic Controls” only.",
          "keywords": ["external authentication", "AAA server", "cryptographic controls"],
          "cross_references": ["ITSAR_CRYPTO:Table1"]
        },
        {
          "id": "2.2.3",
          "title": "Protection against brute force and dictionary attacks",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "Protection against brute force and dictionary attacks that hinder authentication attribute (i.e. password) guessing shall be implemented. In order to achieve higher security, two or more of the measures indicated above shall be mandatorily supported by IP Router: i) timer delay, ii) Blocking an account, iii) CAPTCHA, iv) password blacklist.",
          "keywords": ["Protection against brute force", "dictionary attacks", "timer delay", "Blocking an account"]
        },
        {
          "id": "2.2.4",
          "title": "Enforce Strong Password",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The configuration setting shall be such that IP Router shall only accept passwords that comply with the complexity criteria.",
          "keywords": ["passwords", "complexity criteria"],
          "sub_requirements": [
            {
              "id": "2.2.4.a",
              "text": "Absolute minimum length of 8 characters. Password shall mandatorily comprise all the following four categories: uppercase, lowercase, digit, special character.",
              "obligation": "SHALL"
            },
            {
              "id": "2.2.4.b",
              "text": "The minimum length of characters in the passwords and the set of allowable special characters shall be configurable by the operator.",
              "obligation": "SHALL"
            },
            {
              "id": "2.2.4.f",
              "text": "Passwords shall not be stored in clear text in the system; passwords shall be salted and hashed.",
              "obligation": "SHALL"
            }
          ]
        },
        {
          "id": "2.2.5",
          "title": "Inactive Session Timeout",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "An OAM user interactive session shall be terminated automatically after a specified period of inactivity. It shall be possible to configure an inactivity time-out period.",
          "keywords": ["terminated automatically", "inactivity time-out period"]
        },
        {
          "id": "2.2.6",
          "title": "Password Changes",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "Password change shall be enforced after initial login. IP Router shall enforce password expiry. Previously used passwords shall not be allowed up to a certain number (Password History) minimum 3.",
          "keywords": ["password expiry", "Password History", "minimum 3"]
        },
        {
          "id": "2.2.8",
          "title": "Removal of predefined or default authentication attributes",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "Predefined or default authentication attributes shall be deleted or disabled. Such authentication attributes shall be changed by automatically forcing a user to change it on first time login.",
          "keywords": ["Predefined or default authentication attributes", "deleted or disabled"]
        }
      ]
    },
    {
      "id": "2.3",
      "title": "Software Security",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.3.1",
          "title": "Secure Update",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "IP Router shall support software package integrity validation via cryptographic means, e.g., digital signature using Secure cryptographic controls prescribed in Table 1.",
          "keywords": ["software package integrity validation", "digital signature"],
          "cross_references": ["ITSAR_CRYPTO:Table1"]
        },
        {
          "id": "2.3.3",
          "title": "Source code security assurance",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "compliance_by_undertaking": True,
          "evidence_type": "undertaking",
          "text": "OEM shall follow best security practices including secure coding... Also, OEM shall submit the undertaking as below: Industry standard best practices of secure coding have been followed",
          "keywords": ["secure coding", "undertaking"]
        },
        {
          "id": "2.3.4",
          "title": "Known Malware and backdoor Check",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "compliance_by_undertaking": True,
          "evidence_type": "undertaking",
          "text": "OEM shall submit an undertaking stating that IP Router is free from all known malware and backdoors.",
          "keywords": ["malware", "backdoors", "undertaking"]
        },
        {
          "id": "2.3.6",
          "title": "Unnecessary Service Removal",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "is_prohibition": True,
          "text": "IP Router shall not support following services: a. FTP b. TFTP c. Telnet d. rlogin, RCP, RSH e. HTTP f. SNMP v1 and v2 g. SSHv1 h. TCP/UDP Small Servers i. Finger j. BOOTP server k. CDP, LLDP l. IP Identification Service m. PAD n. MOP",
          "keywords": ["ftp", "tftp", "telnet", "http", "snmpv1", "snmpv2", "sshv1", "cdp", "lldp"]
        },
        {
          "id": "2.3.8",
          "title": "Secure Time Synchronization",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "IP Router shall establish a secure communication channel strictly using Secure cryptographic controls... with NTP/PTP server. IP Router shall support NTPv4 or later version to ensure secure time synchronization.",
          "keywords": ["secure communication channel", "NTP", "PTP", "NTPv4"]
        }
      ]
    },
    {
      "id": "2.4",
      "title": "System Secure Execution Environment",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.4.1",
          "title": "No unused functions",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "is_prohibition": True,
          "text": "Unused functions i.e. the software and hardware functions which are not needed for operation or functionality of the IP Router shall be permanently deactivated.",
          "keywords": ["unused functions", "permanently deactivated"]
        },
        {
          "id": "2.4.2",
          "title": "No unsupported components",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "compliance_by_undertaking": True,
          "evidence_type": "undertaking",
          "text": "OEM to ensure that the IP Router shall not contain software and hardware components that are no longer supported... An undertaking in this regard shall be provided by OEM.",
          "keywords": ["unsupported components", "end-of-life", "undertaking"]
        }
      ]
    },
    {
      "id": "2.5",
      "title": "User Audit",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.5.1",
          "title": "Audit trail storage and protection",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The security event log of IP Routers shall be access controlled (file access rights), so only privilege users shall have access to read the log files but shall not be allowed to delete the log files.",
          "keywords": ["security event log", "access controlled", "not be allowed to delete"]
        },
        {
          "id": "2.5.2",
          "title": "Audit Event Generation",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The IP Router shall log all security events with unique System References such as IP Address, MAC address, hostname, etc.",
          "keywords": ["log all security events"],
          "sub_requirements": [
            {
              "id": "2.5.2.1",
              "text": "Records any user’s incorrect login attempts to the IP router (Mandatory)",
              "obligation": "SHALL",
              "is_table_row": True
            },
            {
              "id": "2.5.2.2",
              "text": "Records any access attempts to accounts that have system privileges. (Mandatory)",
              "obligation": "SHALL",
              "is_table_row": True
            },
            {
              "id": "2.5.2.3",
              "text": "Records all account administration activity, i.e. configure, delete, copy, enable, and disable. (Mandatory)",
              "obligation": "SHALL",
              "is_table_row": True
            }
          ]
        }
      ]
    },
    {
      "id": "2.6",
      "title": "Data Protection",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.6.2",
          "title": "Cryptographic Module Security Assurance",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "compliance_by_undertaking": True,
          "evidence_type": "undertaking",
          "text": "Cryptographic module embedded inside the IP Router... is designed and implemented in compliance with FIPS 140-2 or later... undertaking by the OEM in specified format along with self-certified test reports.",
          "keywords": ["FIPS 140-2", "undertaking"]
        }
      ]
    },
    {
      "id": "2.11",
      "title": "Web Servers",
      "chapter": "CSR",
      "requirements": [
        {
          "id": "2.11.1",
          "title": "HTTPS",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": ["web_interface"],
          "text": "The communication between Web client and Web server shall be protected strictly using the Secure cryptographic controls prescribed in Table1.",
          "keywords": ["HTTPS", "Web client and Web server", "protected strictly"],
          "cross_references": ["ITSAR_CRYPTO:Table1"]
        }
      ]
    },
    {
      "id": "3.1",
      "title": "Routing Related Requirements",
      "chapter": "SSR",
      "requirements": [
        {
          "id": "3.1.1",
          "title": "Control Plane Traffic",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "To prevent such issues, IP Router shall implement control plane policing mechanisms to monitor, filter, and rate-limit control plane traffic, thereby ensuring the stability and security of the network.",
          "keywords": ["control plane policing", "rate-limit control plane traffic"]
        },
        {
          "id": "3.1.2",
          "title": "NAPT (Network Address Port Translation) services support",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": ["napt"],
          "text": "If IP Router supports NAPT services, it shall have protection mechanism against possible attacks such as NAT Traversal attacks, Pin hole attacks and NAT Slipstreaming Etc.",
          "keywords": ["NAPT", "NAT Traversal attacks", "NAT Slipstreaming"]
        },
        {
          "id": "3.1.6",
          "title": "Avoidance of Routing Loops",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "IP Router shall implement routing loop prevention mechanisms such as split horizon, poison reverse, hold down timers etc.",
          "keywords": ["routing loop prevention", "split horizon", "poison reverse", "hold down timers"]
        },
        {
          "id": "3.1.14",
          "title": "Protection against BGP Hijacking",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": [],
          "text": "The IP Router shall support BGP Prefix origin validation to ensure that the origin AS of route is valid for the advertised routes. The IP Router shall maintain an Origin Validation database consisting of static and dynamic entries (VRP or Validated ROA Payload). The IP Router shall support the RPKI-RTR protocol.",
          "keywords": ["BGP Prefix origin validation", "VRP", "ROA", "RPKI-RTR protocol"]
        }
      ]
    },
    {
      "id": "3.10",
      "title": "Wi-Fi Access Related",
      "chapter": "SSR",
      "requirements": [
        {
          "id": "3.10.6",
          "title": "Cryptographic Algorithm selection for Wi-Fi Access",
          "obligation": "SHALL",
          "applicable_router_types": ["conventional", "sdn", "cloud_native", "virtual", "cloud_managed"],
          "required_capability_flags": ["wifi"],
          "text": "Wi-Fi capable Network product shall support WPA2-PSK with AES-128 or higher as default standard. Additionally, WPA2 version must support PMF (Protected Management Frames). All types of Wi-Fi capable Network products shall also support WPA3 and WPA shall not be supported.",
          "keywords": ["WPA2-PSK", "AES-128", "PMF", "WPA3"]
        }
      ]
    }
  ]
}

os.makedirs("c:/Users/yugan.dhar/OneDrive - Incedo Technology Solutions Ltd/Documents/RAG PRS/backend/app/knowledge/data", exist_ok=True)
with open("c:/Users/yugan.dhar/OneDrive - Incedo Technology Solutions Ltd/Documents/RAG PRS/backend/app/knowledge/data/itsar_router_v2.json", "w") as f:
    json.dump(data, f, indent=2)
