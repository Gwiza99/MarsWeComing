import mysql.connector
import math
import time
import maskpass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich import box

import pyfiglet

console= Console()
connection= mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="trackitboardit"
    
)
cursor=connection.cursor(dictionary=True)
def show_title():
    ascii_art=pyfiglet.figlet_format("UMUDENDEZO",font='small')
    title_text=Text(ascii_art, style="bold green")
    subtitle=Text("TrackItBoardIt / Kigali,Rwanda",style="dim cyan")
    console.print(Panel(title_text, subtitle=subtitle,border_style="green"))
    
def divider():
    console.print("[dim]  [/dim]")
    

class User():
    def create_account(self):
        divider()
        console.print(Panel("[bold cyan]Create an Account[/bold cyan]",border_style="cyan"))
        identity=input("Gukora konti nk'umushoferi cg umugenzi?/Do you want an account as a passenger or driver?")
        if identity.lower()=="driver":
            name=Prompt.ask("[green]?[/green] Izina/Create any username")
            pword= maskpass.askpass(prompt="Umubare w'ibanga/Password: ", mask="*")
            cursor.execute("select username from drivers where username=%s ",(name,))
            row=cursor.fetchone()
            if row:
                console.print("[red]Iryo zina ryarakoreshejwe./The username already exists[/red]")
            else:
                cursor.execute("insert into drivers (username,pin ) values (%s,%s)",(name,pword))
                console.print("[green] Konti yakozwe!/Successfully created an account!!![/green]")
                
        elif identity.lower()=="passenger":
            name=Prompt.ask("[green]?[/green] Izina/Create any username")
            pword= maskpass.askpass(prompt="?Umubare w' ibanga/Password: ", mask="*")
            cursor.execute("select username from passengers where username=%s ",(name,))
            row=cursor.fetchone()
            if row:
                console.print("[red]Iryo zina ryarakoreshejwe/The username already exists[/red]")
            else:
                cursor.execute("insert into passengers (username,pin ) values (%s,%s)",(name,pword))
                console.print("[green]Konti yakozwe!!/Successfully created n account!!![/green]")
        else:
            console.print("[yellow]Uwomukoresha ntabonetse!/That user is not found![/yellow]")
            
                    # ppl=cursor.execute("select *  from passengers")
                    # print(ppl)
        # connection.commit()
        
            
            
    def login(self):
        while True:
            divider()
            console.print(Panel('[bold cyan]Injira/Login[/bold cyan]',border_style="cyan"))
            identity=input("Injira muri konti nk' umugenzi cg umushoferi/Login as Passenger or Driver?")
            
            
            
            
            if identity.lower() == "passenger":
                name=Prompt.ask("[green]?Izina/Username[/green]")
                pword= maskpass.askpass(prompt="?Umubare w' ibanga/Password: ", mask="*")
        
                cursor.execute("select * from  passengers where username=%s AND pin=%s ",(name,pword))
            
                user = cursor.fetchone()
                if user:
                    console.print(f"\n[bold green]/Urakaza neza/Welcomeee back,{name}![/bold green] ")
                    return identity
                else:
                    console.print("[red]Kosora izina cg umubare w' ibanga/Mind checking ur credentials!Try again[/red]")
                    
            elif identity.lower()=="driver":
                name=Prompt.ask("[green]?[/green]Username")
                pword= maskpass.askpass(prompt="?Password: ", mask="*")
                cursor.execute("select * from  drivers where username=%s AND pin=%s ",(name,pword))
                user = cursor.fetchone()
                if user:
                    console.print(f"[bold green]Welcomeee,{name}![/bold green] [dim yellow]Cana GPS/Turn on GPSTracker[/dim yellow]")
                    return identity
                else:
                    console.print("[red]Kosora izina cg umubare w'ibanga/Mind checking ur credentialss[/red]")
                    
            else:
                console.print("[yellow]Uwo mukoresha ntabwo abaho/The user is not found![/yellow]")
            

class Driver:
    def __init__(self):
        self.current_location=''
        self.speed=0
        self.route=[]
        self.remainig_seats=0
    def get_info(self):
        divider()
        console.print(Panel("[bold yellow] Shyiramo amakuru ya bisi/Enter Bus Info[/bold yellow]", border_style="yellow"))
        self.current_location=Prompt.ask("[green]Ugezehe/Driver's current location[/green]")
        self.speed=int(Prompt.ask("[green]Umuvuduko/Bus's curent speed(km/h)[/green]"))
        self.route=Prompt.ask("[green]?Aho uranyura/The bus's route from the starting terminal to the last terminal[/green]")
        self.remainig_seats=Prompt.ask("[green]?Imyanya isigaye/seats available[/green] ")
        with console.status("[cyan]Amakuru ari kubikwa/Saving bus info...[/cyan]",spinner="dots"):
            time.sleep(2)
            
        cursor.execute("insert into buses (current_locaction, speed, route, remainig_seats) VALUES (%s, %s, %s, %s)",
        (self.current_location, self.speed, self.route, self.remainig_seats))
        connection.commit()
        
class Passenger():
    def __init__(self):
        self.destination=''
        self.current_stop=''
    def get_info(self):
        divider()
        console.print(Panel("[bold cyan] Amakuru y'umugenzi/Passenger's info[/bold cyan]",border_style="cyan"))
        self.destination=Prompt.ask("[green]Ugiyehe/What's your destination[/green]").strip().lower()
        self.current_stop=Prompt.ask("[green]Uri kuyihe alert?/Which stop are you at?[/green]").strip().lower()

class Calculations:

    def get_coordinates(self, stop_name):
        cursor.execute("select latitude, longitude FROM stops_coordinates WHERE LOWER(stop_name) = %s",(stop_name.lower(),))
        return cursor.fetchone()

    def calculate_distance(self, bus_location, passenger_stop):
        p_coordinates = self.get_coordinates(passenger_stop)
        
        if not p_coordinates:
            return None
        
        b_coordinates = self.get_coordinates(bus_location)
        if not b_coordinates:
            return None

        p_lat = p_coordinates["latitude"]
        p_long = p_coordinates["longitude"]

        b_lat = b_coordinates["latitude"]
        b_long = b_coordinates["longitude"]

        
        R = 6371  
        d_lat = math.radians(p_lat - b_lat)
        d_lon = math.radians(p_long - b_long)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(b_lat)) * math.cos(math.radians(p_lat)) * math.sin(d_lon/2)**2
        distance = R * 2 * math.asin(math.sqrt(a))

        return distance
    
    def filter_buses(self, stop, passenger_destination):
    
        results = []
        cursor.execute("select * from buses")
        buses=cursor.fetchall()
        for bus in buses:
                        
            if bus["remainig_seats"] == 0:
                continue
            
            route=[ stop.strip().lower() for stop in bus['route'].split(',')]
            if stop not in route or passenger_destination not in route:
                print("Busi ntabwo ica aho uri./Destination not in route.")
                continue
            if route.index(stop)>=route.index(passenger_destination):
                print("Warenze aho ujya cg wageze aho ujya./ You're past your destination or you arrived.")
                continue
            distance = self.calculate_distance(bus["current_locaction"],stop)
            if distance is None:
                print(" coordinates not found")
                continue
            if bus["speed"] == 0:
                print(" speed is 0")
                continue
            eta = (distance / bus["speed"]) * 60
            results.append({"bus_id": bus["bus_id"],"distance": distance,"eta": eta,"remainig_seats": bus["remainig_seats"]})
        results.sort(key=lambda x: x["eta"])

        return results
        
class Display:

    def show(self, results):
        divider()
        if not results:
            console.print(Panel("[red]Nta bisi ihari/No buses available for route right now![/red]",border_style="red"))
            return
        table=Table(
            title="[bold cyan] Bisi zihari/Available Buses [/bold cyan]",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
            show_lines=True 
        )

        table.add_column("Bus ID",style='yellow', justify="center")
        table.add_column("Distance/Intera",style='green', justify="center")
        table.add_column("ETA/Umwanya usigaye",style='magenta', justify="center")
        table.add_column("Seats/Imyanya",style='cyan', justify="center")

        for bus in results:
            table.add_row(
                f"Bus {bus['bus_id']} ",
                f"{bus['distance']:.2f} km bibura/km away",
                f"iraza mu minota/will arrive in {bus['eta']:.2f} minutes",
                str(bus['remainig_seats'])
            )
        console.print(table)
user=User()
dri=Driver()
pas=Passenger()
calc=Calculations()
display=Display()

show_title()
while True:
    divider()
    console.print("[bold cyan]1.Injira muri konti yawe/Login[/bold cyan]")
    console.print("[bold cyan]2.kora konti/Create an account[/bold cyan]")
    console.print("[bold cyan]3.Sohoka/Exit[/bold cyan]")
    
    n=int(Prompt.ask("[magenta]Amahitamo yawe/Your choice[/magenta]"))
    
    if n==1:
        identity=user.login()
        
        if identity=="passenger":
            pas.get_info()
            with console.status("[cyan] Gushaka bisi.../Searching for buses...[/cyan]",spinner="dots"):
                time.sleep(1.5)
            result=calc.filter_buses(pas.current_stop,pas.destination)
            
            display.show(result)
        else:
            dri.get_info()
    elif n==2:
        user.create_account()
        
    else:
        console.print("\n[bold green] Urugendo rwiza!/Bye Bye! Safe journey![/bold gree]\n")
        exit()
        
    
    
        
        
        
        
        
    