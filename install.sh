#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo cp systemd/cyberus.service /etc/systemd/system/
sudo systemctl daemon-reexec
sudo systemctl enable cyberus
sudo systemctl start cyberus
echo "CyBerus installed and running at http://localhost:5000"
