from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *
import datetime

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    
    if session["user_id"]:
    
        result = db.execute("SELECT* from portfolio where userid = :uid ", uid = session["user_id"])
                
        total_cash= db.execute("SELECT cash from users where id = :uid", uid = session["user_id"])
        for i in range(len(result)):
            result[i]['price'] = usd(result[i]['price'])
            result[i]['total'] = usd(result[i]['total'])
        cash =  usd(total_cash[0]['cash'])
    
        initial_cash = 10000
        initial_cash = usd(initial_cash)
        
     
        return render_template("index.html", result = result, cash=cash, initial_cash =initial_cash, banner=request.args.get('banner'))
        
    else:
        return redirect(url_for("login"))

@app.route("/change_Password", methods=["GET", "POST"])
@login_required 
def change_Password():
    if request.method == "POST":
        old = request.form.get("OldPass")
        if old =="":
           return apology("Must enter old password")
        
        old_row_hash = db.execute("SELECT hash from users where id = :uid ", uid = session["user_id"])
       
        if not pwd_context.verify(old, old_row_hash[0]['hash']):
           return apology("Incorrect old password!")
        
        new = request.form.get("NewPass")
        if new == "":
            return apology("Must enter new Password!")
          
          
        again_new =  request.form.get("againNewPass") 
        if again_new =="" or again_new != new:
            return  apology("Incorrect password! Enter again.")
            
        hash_password = pwd_context.hash(new)
        db.execute("UPDATE users set hash = :newHash WHERE id = :id", newHash = hash_password, id=  session["user_id"])
        
        notify = 0
        return redirect(url_for("index", banner=notify))
    else:
        return render_template("newPass.html")
   


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":
        
        
        
        symbol = request.form.get("symbol") 
        shares_count = request.form.get("shares")
        
        if symbol=="" or not symbol.isalpha():
           return apology("must provide symbol/incorrect symbol!")
       
        if  not (shares_count).isdigit():
           return apology("Must provide correct number of shares!")
           
        if shares_count =="" or int(shares_count) <= 0 :
           return apology("Must provide shares/ Correct number of shares!")
           
        stock = lookup(request.form.get("symbol"))
        if stock == None:
            return apology("Symbol not exist in stock!")
     
        else:
            cash_row = db.execute("SELECT cash from users where id = :uid", uid = session["user_id"])
            
            
            cash = cash_row[0]['cash']
            price = stock['price']
            total = float(price) * float(shares_count)
            if  cash < total:
                return apology("SORRY! YOU HAVE INSUFFICIENT CASH")
            else:
                #update cash of that user
                
                db.execute("UPDATE users set cash = cash - :c  where id = :uid " ,c =total,uid = session["user_id"])
                name = stock['name']
                price =stock['price']
                
                
                now = datetime.datetime.now()
                db.execute("INSERT INTO history (userid, symbol ,shares, price, TimeDate) values(:uid, :symbol, :share, :price, :TD)"
                , uid = session["user_id"], symbol = symbol.upper(), share = int(shares_count), price = price, TD= str(now))
                
                rows =db.execute("SELECT * FROM portfolio WHERE userid = :uid AND symbol = :symbol" ,uid = session["user_id"], symbol = symbol.upper())
                
                if len(rows) == 0:          # user has bought a new stock
                    db.execute("INSERT INTO portfolio (userid, symbol, name, shares, price, total) VALUES(:uid, :symbol, :name, :shares, :price, :total)",
                    uid =  session["user_id"], symbol =symbol.upper(), name =name, shares = int(shares_count), price = price, total =total)
                    
                else: #update shares values and total
                    total_row =  db.execute("SELECT total FROM portfolio where userid = :uid AND symbol = :symbol", uid = session["user_id"], symbol = symbol.upper())
                    total  += total_row[0]['total']
                    db.execute("UPDATE portfolio set total = :t WHERE userid = :uid AND symbol = :symbol", t=total ,uid = session["user_id"], symbol = symbol.upper())
                    shares_row =  db.execute("SELECT shares FROM portfolio where userid = :uid AND symbol = :symbol", uid = session["user_id"], symbol = symbol.upper())
                    s = shares_row[0]['shares']
                    s = int(s)+ int(shares_count)
                    db.execute("UPDATE portfolio set shares = :shares WHERE userid = :uid AND symbol = :symbol", shares = int(s) ,uid = session["user_id"], symbol = symbol.upper())
            
        notify =1
        return redirect(url_for("index", banner=notify))
    else:
        
        return render_template("buy.html")
    
   

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    history_rows = db.execute("SELECT * FROM history where userid= :id", id = session["user_id"])
    for i in range(len(history_rows)):
            history_rows[i]['price'] = usd(history_rows[i]['price'])
           
    return render_template("history.html", result = history_rows)
    
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]['hash']):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    
    if request.method == "POST":
        
       
        
        stock = lookup(request.form.get("Symbol")) 
    
        if  stock != None:
           
            return render_template("quoted.html", stock=stock)
            
        else:
            
            return apology("Sorry! something went wrong")
        
      
      #  render_template("quoted.html", name= result.name, price = result.price, symbol =result.symbol)
       
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    session.clear()
    
    if request.method == "POST":
       
        if not request.form.get("username"):        #if username is not provided
            return apology("must provide username")
        
        elif not request.form.get("password"):    #if password is not provided
            return apology("must provide password")
            
        elif not request.form.get("confirm_password"):    #if passwords dont match
            return apology("must provide password again")
            
        elif request.form.get("password")!= request.form.get("confirm_password"):
            return apology("both passwords must be same")
            
        rows = db.execute("SELECT * FROM  users WHERE username = :username", username = request.form.get("username"))
        
        if len(rows) != 0:
            return apology("username already exists!")
            
            
        username = request.form.get("username")
        password = request.form.get("password")
        hash_password = pwd_context.hash(password)
    
        
        db.execute("INSERT INTO users (username,hash) VALUES(:username,:hash)", username=  request.form.get("username") ,hash =hash_password)
        rows_id = db.execute("SELECT * FROM  users WHERE username = :username", username = request.form.get("username"))
        
        session["user_id"] = rows_id[0]["id"]
        notify =2
        return redirect(url_for("index", banner=notify))

        
    else:
        return render_template("register.html")
     

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    
    if request.method == "POST":
        
        symbol = request.form.get("symbol") 
        shares = request.form.get("shares")
        
        ### symbol provided or not
        if symbol=="" or not symbol.isalpha():
           return apology("must provide symbol/incorrect symbol!")
       
        if  not (shares).isdigit():
           return apology("Must provide correct number of shares!")
        if shares =="" or int(shares) == 0 :
           return apology("Must provide shares!")
        
        ##symbol exists in stock or not
        stock =lookup(request.form.get("symbol"))
        
        if stock == None:
            return apology("Symbol not exist in stock!")
            
        ### symbol owned or not
        symbol_exist  =db.execute("SELECT * from portfolio where userid = :id and symbol = :symbol", id = session["user_id"], symbol =symbol.upper())
        
        if len(symbol_exist) == 0:
            return apology("Symbol not owned/provide correct shares!")
            
     
        rows =db.execute("SELECT * from portfolio where userid = :id AND symbol = :s ", id = session["user_id"], s = symbol.upper())
        
        shares_check = rows[0]['shares']
        
       
        if int(shares) > shares_check:
            return apology("You have insufficient number of shares to sell!")
            
        total = stock['price']* int(shares)
       
        ## inserting in history table
        now = datetime.datetime.now()
        db.execute("INSERT INTO history (userid, symbol, shares, price, TimeDate) values(:uid, :symbol, :shares, :price, :TD)",
        uid = session["user_id"], symbol = symbol.upper() , shares = -int(shares), price= stock['price'], TD= str(now))
        
        db.execute("UPDATE portfolio set shares = shares - :s where userid = :id and symbol = :symbol", s = int(shares),id = session["user_id"], symbol =symbol.upper())
            
        shares_check_rows = db.execute("SELECT shares from portfolio where userid = :id and symbol = :symbol", id = session["user_id"], symbol =symbol.upper())
        if int(shares_check_rows[0]['shares'])==0 :   # shares ended #delete entire row
            db.execute("DELETE FROM portfolio where userid = :id and symbol = :symbol", id = session["user_id"], symbol =symbol.upper() )
            
            ## update total and cash 
        else:   
         
            db.execute("UPDATE portfolio set total = total -:t WHERE userid = :uid AND symbol = :symbol", t=total ,uid = session["user_id"], symbol = symbol.upper())
            
        db.execute("UPDATE users set cash = cash + :c  where id = :uid " ,c =total,uid = session["user_id"])
            
        notify=3
        return redirect(url_for("index", banner=notify))
 
    else:
        return render_template("sell.html")
    
    
    
    
    
    
    
    
    
    
