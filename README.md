\# Kapture Collections Voicebot



\## Overview



This project is a Python-based prototype of a Collections Voicebot for handling overdue loan payment conversations.



The bot retrieves customer account information from a mock Flask backend, interacts with the customer through a text-based conversation, identifies the customer's response, determines the appropriate collection outcome, invokes backend tool calls when required, and records the final call disposition.



\## Project Workflow



```text

Customer Account

&#x20;      |

&#x20;      v

Mock Flask Backend

&#x20;      |

&#x20;      | GET /customer

&#x20;      v

Collections Voicebot

&#x20;      |

&#x20;      v

Customer Response

&#x20;      |

&#x20;      v

Response Classification

&#x20;      |

&#x20;      +----------------------+

&#x20;      |                      |

&#x20;      v                      v

Payment-related          Escalation

Outcome                  Required

&#x20;      |                      |

&#x20;      |                      v

&#x20;      |              escalate\_to\_agent

&#x20;      |                      |

&#x20;      +----------+-----------+

&#x20;                 |

&#x20;                 v

&#x20;         mark\_disposition

&#x20;                 |

&#x20;                 v

&#x20;         SQLite Database

