function ajaxGet(url, datas, target, modal_target)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if (modal_target != "")
            {
                $('#'+modal_target+"-body").html(data);
                $('#'+modal_target).modal('show');
            }
            else
                if (target != "")
                    $('#'+target).html(data);
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    }); 
};

function ajaxGetAutosave(url, datas, target)
{
    $("body").css("cursor", "progress");
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            $("#"+target).html(data).fadeTo(5000, 500).slideUp(500, function(){
                $("#"+target).slideUp(500);
            });
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){$("body").css("cursor", "default");}
    }); 
};


function ajaxGetRemove(url, datas, target)
{
    $.ajax({
        url : url,
        type : 'GET',
        data : datas,
        dataType : 'html',
        beforeSend : function(){},
        success : function(data){
            if(data != "")
                $('#'+target).html(data);
            else
                $('#'+target).remove();
        },
        error : function(e){alert("Error: "+e.responseText);},
        complete : function(){}
    }); 
};

function autoComplete(obj)
{
    url = obj.data("url");
    target = obj.data("target");
    value = obj.val()

    var datas = {};
    var args = obj.data();
    for(var i in args)
        if (i != "url")
            datas[i] = args[i]
    datas['value'] = value;

    ajaxGet(url, datas, target, '');
}

function uploadFile(url, target, token, model_name, obj_id, field, field_id=null)
{
    var fd = new FormData();
	
    var files = (field_id) ? $('#'+field_id)[0].files[0] : $('#'+field)[0].files[0];
    //var token = document.getElementsByName('csrfmiddlewaretoken')[0].value;

    fd.append('target', target);
    fd.append('model_name', model_name);
    fd.append('obj_id', obj_id);
    fd.append('field', field);
    fd.append('file', files);
    fd.append('csrfmiddlewaretoken', token);
	
    $.ajax({
        url: url,
        type: 'post',
        data: fd,
        contentType: false,
        processData: false,
        success: function(data){
            if (target.indexOf("alert") >= 0)
            {
				
                $("#"+target).html(data).fadeTo(5000, 500).slideUp(500, function(){
                    $("#"+target).slideUp(500);
                });
            }
            else
            {
                $('#'+target).html(data);
				$('#'+target).trigger('create');
            }

        },
        error : function(e){alert("Error: "+e.responseText);},
    });
}

function validateEmail(email) {
    var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
}

function validateSlug(text)
{
	var re = /^[A-Za-z0-9]+(._-[A-Za-z0-9]+)*$/
	return re.test(String(text));
}

function validatePassword(pass)
{
	var re = /(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}/
	return re.test(String(pass))
}

function clearHtml(obj)
{
    $(obj).html("");
}

$(document).ready(()=>{
    $("body").on("change", ".autosave", function(e){
        var obj = $(this);
        msg_id = "#" + obj.attr("id") + "__msg";
        if (obj[0].checkValidity())
        {
            $(msg_id).html("");
            obj.removeClass("invalid");

            model_name = obj.data("model-name");
            obj_id = obj.data("obj-id");
            url = obj.data("url");
            target = obj.data("target");
            field = obj.attr("name");

            if (obj.data("bool"))
                if (obj.is(':checked'))
                    value = "True";
                else
                    value = "False";
            else
                value = obj.val();

            datas = {'model_name': model_name, 'obj_id': obj_id, 'field': field, 'value': value};
            ajaxGetAutosave(url, datas, target);
            e.preventDefault();
        }
        else
        {
            $(msg_id).html(obj.attr("title"));
            obj.removeClass("valid").addClass("invalid");
        }
    });

    $("body").on("click", ".autoremove", function(e){
        if (confirm("Esta seguro/a de que desea borrar el elemento?"))
        {
            model_name = $(this).data("model-name");
            obj_id = $(this).data("obj-id");
            url = $(this).data("url");
            target = $(this).data("target");
            datas = {'model_name': model_name, 'obj_id': obj_id};
            ajaxGetRemove(url, datas, target);
            if ($(this).data("hide"))
                $("#" + $(this).data("hide")).hide();
            e.preventDefault();
        }
    });

    $("body").on("click", ".ark", function(e){
        var obj = $(this);
        if (((obj.data("confirm")) && confirm(obj.data("confirm"))) || !(obj.data("confirm")))
        {
            url = obj.data("url");
            var target = "";
            var target_modal = "";
            if (obj.data("target"))
                target = obj.data("target");
            if (obj.data("target-modal"))
                target_modal = obj.data("target-modal");

            var datas = {};
            var args = obj.data();
            for(var i in args)
                if (i != "url")
                    datas[i] = args[i]
            ajaxGet(url, datas, target, target_modal);

            if (obj.data("clear"))
                clearHtml($("#" + obj.data("clear")));
            e.preventDefault();
        }
    });

    $("body").on("keyup", ".autocomplete", function(e){
        let target = $(this).data("target")
        $(`#${target}`).html("<i class='fas fa-spinner fa-spin'></i> Searching...");
        var obj = $(this);
        setTimeout(function(){
            autoComplete(obj);
        }, 1000);
        e.preventDefault();
    });

    $("body").on("change", ".autoupload", function(e){
        url = $(this).data("url");
        target = $(this).data("target");
        model_name = $(this).data("model-name");
        obj_id = $(this).data("obj-id");
        token = $(this).data("csrf-token");
        field = $(this).attr("name");
		field_id = $(this).attr("id");
        uploadFile(url, target, token, model_name, obj_id, field, field_id);
        e.preventDefault();
    });
});
