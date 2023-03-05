import datetime
from product import Product
from database import DataBase
import PySimpleGUI as sg
import requests
import schedule
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import webbrowser
import sys
from pygame import mixer

db = DataBase()
mixer.init()


def main():
    right_click_menu = ['', ['Delete', 'Update', 'Add alerts', 'Remove alerts', 'Go to website']]
    product_list = [x for x in db.get_product_list()]
    sg.theme('DarkAmber')
    headings = ['ALERT', 'Name', 'Current Price (RON)', 'Status', 'Last Checked', 'Price Alert', 'Stock Alert', 'url']
    layout = [
        [sg.Text('Product list')],

        [sg.Table(product_list, headings=headings, justification='left', key='-TABLE-',
                  right_click_selects=True, enable_events=True, right_click_menu=right_click_menu,
                  max_col_width=40, vertical_scroll_only=False, expand_x=True)],

        [sg.Button('Add product', key='-ADD_BTN-'), sg.Button('Update All', key='-UPDATE_ALL_BTN-'),
         sg.Push(),
         sg.Text('Auto refresh every (minutes) '),
         sg.InputText(size=(5, 1), key='-AUTO_REFRESH_INPUT-'),
         sg.Button('Save', key='-AUTO_REFRESH_BTN-')],

        [sg.Push(),
            sg.Text(text='', visible=False, key='-TIMER_DISPLAY-')],
        [sg.HorizontalSeparator(pad=(0, 40))],
        [sg.Canvas(key='-CANVAS-', visible=False)],
    ]

    window = sg.Window('EMAG price tracker', layout, size=(1100, 300), resizable=True, finalize=True)

    while True:
        schedule.run_pending()
        display_timer(window)
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED:
            break

        # MAIN PRODUCT TABLE #######################################################################################

        if event == '-TABLE-':
            window.Size = (1100, 700)
            product_list = [x for x in db.get_product_list()]
            try:
                graph_widget.get_tk_widget().forget()
            except NameError:
                pass
            window['-CANVAS-'].update(visible=True)
            window['-AUTO_REFRESH_BTN-'].update('Save')
            select_index = values[event][0]
            product_name = product_list[select_index][1]
            product_history = db.get_price_history(product_name)
            graph_widget = make_graph(product_history, window, product_name)

        # MAIN WINDOW BUTTONS #######################################################################################

        if event == '-ADD_BTN-':
            add_product_window()
            update_table(window)

        if event == '-UPDATE_ALL_BTN-':
            db.update_all()
            update_table(window)

        if event == '-AUTO_REFRESH_BTN-':
            schedule.clear('timer')
            try:
                input_minutes = int(values['-AUTO_REFRESH_INPUT-'])
                if input_minutes < 0 or input_minutes > sys.maxsize:
                    raise ValueError
            except ValueError:
                window['-AUTO_REFRESH_INPUT-'].update('Invalid')
            else:
                window['-AUTO_REFRESH_BTN-'].update('Saved')
                schedule.every(input_minutes).minutes.do(auto_update_all, window).tag('timer')

        # RIGHT CLICK MENU #########################################################################################

        if event == 'Delete':
            try:
                row_selected = product_list[values['-TABLE-'][0]]
            except IndexError:
                sg.popup_error('No product selected', grab_anywhere=True)
            else:
                db.delete_item(row_selected[1])
                update_table(window)

        if event == 'Update':
            try:
                row_selected = product_list[values['-TABLE-'][0]]
                product_name = row_selected[1]
            except IndexError:
                sg.popup_error('No product selected', grab_anywhere=True)
            else:
                db.update_one(product_name)
                update_table(window)

                graph_widget.get_tk_widget().forget()
                product_history = db.get_price_history(product_name)
                graph_widget = make_graph(product_history, window, product_name)

                check_alerts()

        if event == 'Add alerts':
            try:
                row_selected = product_list[values['-TABLE-'][0]]

            except IndexError:
                sg.popup_error('No product selected', grab_anywhere=True)
            else:
                add_price_alert_window(row_selected)
                update_table(window)

        if event == 'Remove alerts':
            try:
                row_selected = product_list[values['-TABLE-'][0]]
            except IndexError:
                sg.popup_error('No product selected', grab_anywhere=True)
            else:
                db.update_price_alert(row_selected, None)
                db.update_stock_alert(row_selected, False)
                check_alerts()
                update_table(window)

        if event == 'Go to website':
            try:
                row_selected = product_list[values['-TABLE-'][0]]
            except IndexError:
                sg.popup_error('No product selected', grab_anywhere=True)
            else:
                product_url = row_selected[7]
                webbrowser.open_new_tab(product_url)

    window.close()


# PLOT LOGIC ############################################################################################


def make_graph(product_history, window, product_name):
    selected_timestamps = [x[1] for x in product_history]
    selected_p_history = [x[0] for x in product_history]
    fig = plt.figure(figsize=(11, 3.7))
    fig.set_facecolor('#2c2825')
    plt.xlabel('', fontsize=14, color='#fdcb52')
    plt.ylabel('RON', fontsize=14, color='#fdcb52')
    plt.xticks(rotation=45, fontsize=8, color='#fdcb52')
    plt.yticks(fontsize=10, color='#fdcb52')
    plt.plot(selected_timestamps, selected_p_history, markerfacecolor='green', marker='*')
    plt.title(f"{product_name}\n", color='#fdcb52')
    plt.tight_layout()
    for x, y in zip(selected_timestamps, selected_p_history):
        plt.annotate(str(y), xy=(x, y), fontsize=10, color='#30260f')
    graph_widget = draw_figure(window['-CANVAS-'].TKCanvas, fig)
    return graph_widget


def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def delete_figure(figure_agg):
    figure_agg.get_tk_widget().forget()


# WINDOW - ADD NEW PRODUCT ###################################################################################


def add_product_window():
    sg.theme('DarkAmber')
    layout = [
        [sg.Text("EMAG url"),
         sg.InputText(size=(50, 1), key='url-box', do_not_clear=False)],

        [sg.Button('Add', key='add-btn'),
         sg.Button('Cancel', key='cancel-btn')]
    ]
    window = sg.Window('Add new product', layout, modal=True, grab_anywhere=True)

    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break
        if event == 'cancel-btn':
            window.close()
        if event == 'add-btn':
            url = values['url-box']
            try:
                product = Product(url)

            except (requests.exceptions.Timeout, requests.exceptions.HTTPError,
                    requests.exceptions.MissingSchema, requests.exceptions.InvalidURL) as e:
                sg.popup_error(e)
            except AttributeError:
                sg.popup_error('Invalid product page.')
            else:
                db.add_product(product)

                window.close()


# WINDOW - ADD PRICE ALERT #################################################################################
def add_price_alert_window(selected_row):
    sg.theme('DarkAmber')
    product_name = selected_row[1]
    price_alert = selected_row[5]
    stock_alert = True if selected_row[6] else False
    display_name = f'{product_name[:80]}...' if len(product_name) > 50 else f'{product_name}'
    layout = [
        [sg.Push(),
         sg.Text(text=f'{display_name}', justification='center')],

        [sg.HorizontalSeparator(color='#fdcb52', pad=(0, 20))],

        [sg.Push(),
         sg.Text(text='Notify me when price drops below (RON): '),
         sg.InputText(size=(10, 1), default_text=price_alert, key='-NOTIFY_INPUT-')
         ],

        [sg.Push(),
         sg.Text(text='Notify me when product is in stock'),
         sg.Checkbox(text='', default=stock_alert, key='-STOCK_CHECK_BTN-')],

        [sg.Push(),
         sg.Button(button_text="Save", key='-SAVE_BTN-'),
         sg.Button(button_text="Cancel", key='-CANCEL_BTN-')]
    ]
    window = sg.Window('Add price alert', layout=layout, modal=True, grab_anywhere=True)
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED:
            break
        if event == '-CANCEL_BTN-':
            window.close()
        if event == '-SAVE_BTN-':
            db.update_stock_alert(selected_row, values['-STOCK_CHECK_BTN-'])
            if values['-NOTIFY_INPUT-']:
                try:
                    input_notify_value = float(values['-NOTIFY_INPUT-'])
                    if input_notify_value < 0:
                        raise ValueError
                except (ValueError, OverflowError):
                    window['-NOTIFY_INPUT-'].update('Invalid price')
                else:
                    db.update_price_alert(selected_row, input_notify_value)

            else:
                product_name = selected_row[1]
                db.update_price_alert(selected_row, None)
            db.update_one(product_name)
            check_alerts()
            window.close()

# PRODUCT UPDATING ##################################################################################################


def update_table(window):
    new_product_list = [x for x in db.get_product_list()]
    window.Element('-TABLE-').update(values=new_product_list)


def auto_update_all(window):
    db.update_all()
    update_table(window)
    check_alerts()


def check_alerts():
    names_to_notify = db.get_products_to_notify()
    if names_to_notify:
        for name in names_to_notify:
            db.add_notify(name[0])
            mixer.music.load('./chime.mp3')
            mixer.music.play()


def display_timer(window):
    if schedule.idle_seconds():
        seconds_until_job = schedule.idle_seconds()
        delta_next = datetime.timedelta(seconds=int(seconds_until_job))
        window['-TIMER_DISPLAY-'].update(f'Next autoupdate in {delta_next}', visible=True)


if __name__ == "__main__":
    main()
