import azure.functions as func
import logging

app = func.FunctionApp()

@app.timer_trigger(schedule="0 0 9 * * 1-5", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def check_canteen_menu(myTimer: func.TimerRequest) -> None:
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Starting to check the canteen menu...')

