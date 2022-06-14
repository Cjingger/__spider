# !/bin/bash
task_time=`date +"%Y-%m-%d%H:%M:00"`
echo "task_time="${task_time}
file_path="/"$1"/project/flight_spider/city_tw_data_3U.txt"
start_file_index=1
end_file_index=1
from_date=1
to_date=1
only_lowest_price=1
cd /$1/project/flight_spider/flight_spider
python3 start.py $file_path $start_file_index $end_file_index $from_date $to_date $only_lowest_price $task_time