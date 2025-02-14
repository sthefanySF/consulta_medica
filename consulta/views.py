import tempfile
import os
from audioop import reverse
from imaplib import _Authenticator
from multiprocessing import AuthenticationError
from django.http import HttpResponse, JsonResponse
from django.views.generic.edit import CreateView
from django.views.generic import DetailView
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.shortcuts import render

# from consulta.forms import AdministrativoForm, AgendamentoForm, AgendamentoReagendarForm, AtendimentoForm,
# JustificativaCancelamentoForm, PacienteForm, PesquisaAgendamentoForm, ProfissionaldasaudeForm
import json
from django.http import JsonResponse
from consulta.forms import *
from django.views.decorators.http import require_POST
from consulta.models import ArquivoPaciente, Atendimento, Paciente, Administrativo
from consulta.models import Agendamento, Paciente, Profissionaldasaude, AtestadoMedico, ReceitaMedica
from datetime import date
from django.shortcuts import render
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

from django.contrib import messages

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password

from django.template.loader import render_to_string
import io

from django.template.response import TemplateResponse


# PARA ENVIAR E-MAIL
from django.core.mail import send_mail
from sistema_medico.settings import EMAIL_HOST_USER
from django.conf import settings

# para weasyprint e visualizar pdf
from django.http import FileResponse
from django.template.loader import get_template
from playwright.sync_api import sync_playwright


#filtrar pacientes
from django.core import serializers
from django.core.serializers import serialize

# permissoes de usuario
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin


from django.shortcuts import render
# from django.core.files.storage import FileSystemStorage


def home(request):
    return render(request, 'home.html')



@login_required
def linha_usuario(request): #mostrar o usuario logado
    user = request.user
    context = {
        'user': user,
    }

    profissional_saude = Profissionaldasaude.objects.filter(usuario=user).first()
    context['profissional_saude'] = profissional_saude

    administrativo = Administrativo.objects.filter(usuario=user).first()
    context['administrativo'] = administrativo

    print("Context:", context)  # Debugging

    return render(request, 'linha_usuario.html', context)

def logar(request):
    if request.user.is_authenticated:
        return redirect('agendamentoListagem')
    if request.method == 'POST':
        # form = AuthenticationForm(request, request.POST)
        usuario = request.POST['usuario']
        usuario = usuario.replace('.', '').replace('-', '')
        senha = request.POST['senha']
        user = authenticate(request, username=usuario, password=senha)
        if user is not None:
            if user.is_active:
                login(request, user)
                if request.GET.get('next'):
                    return redirect(request.GET.get('next'))
                return redirect('agendamentoListagem')
            else:
                messages.error(request, 'Usuário inativo. Entre em contato com a administração do sistema.')
        else:
            messages.error(request, 'Usuário ou senha inválidos! Tente novamente.')
    return render(request, 'consultas/login.html', locals())


@login_required()
def sair(request):
    logout(request)
    return redirect('login')

# def login(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(request, username=username, password=password)
#             if user:
#                 login(request, user)
#                 return redirect('home')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'consultas/login.html', {'form': form})
# #



@login_required
def listar_pacientes(request):
    pacientes = Paciente.objects.all().order_by('nome')
    form = PacienteForm()
    return render(request, 'consultas/listagem_pacientes.html', {'pacientes': pacientes, 'form': form})

@login_required
def paciente_editar(request, pk):
        paciente = get_object_or_404(Paciente, pk=pk)

        if request.method == 'POST':
            form = PacienteForm(request.POST, instance=paciente)
            if form.is_valid():
                form.save()
                messages.success(request, 'Cadastrado atualizado!')
               
                return redirect('pacienteListagem')
        else:
            form = PacienteForm(instance=paciente)

        return render(request, 'consultas/editar_paciente.html', {'form': form, 'paciente': paciente})

@require_POST
def paciente_excluir(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    
    try:
        paciente.delete()
        messages.success(request, 'Paciente excluído')
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('pacienteListagem')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        return render(request, 'consultas/excluir_paciente.html', {'paciente': paciente})

#modal
@login_required
def editar_paciente(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("Recebendo POST request via AJAX")
        id = request.POST.get('id')
        print(f"ID recebido: {id}")
        paciente = get_object_or_404(Paciente, id=id)
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            print("Formulário válido e salvo com sucesso.")
            return JsonResponse({'success': True})
        else:
            print(f"Formulário inválido: {form.errors}")
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        print("Recebendo GET request")
        id = request.GET.get('id')
        paciente = get_object_or_404(Paciente, id=id)
        form = PacienteForm(instance=paciente)
        context = {
            'form': form,
            'paciente': paciente
        }
        return render(request, 'consultas/editar_paciente.html', context)

def is_administrativo(user):
    return user.groups.filter(name='administrativo').exists()

@login_required
def listar_administrativo(request):
    administrativo = Administrativo.objects.all()
    form = AdministrativoForm()
    return render(request, 'consultas/listagem_administrativo.html', {'administrativo': administrativo, 'form': form})

# modal
@login_required
def editar_administrativo(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("Recebendo POST request via AJAX")
        id = request.POST.get('id')
        print(f"ID recebido: {id}")
        administrativo = get_object_or_404(Administrativo, id=id)
        form = AdministrativoForm(request.POST, instance=administrativo)
        if form.is_valid():
            form.save()
            print("Formulário válido e salvo com sucesso.")
            return JsonResponse({'success': True})
        else:
            print(f"Formulário inválido: {form.errors}")
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        print("Recebendo GET request")
        id = request.GET.get('id')
        administrativo = get_object_or_404(Administrativo, id=id)
        form = AdministrativoForm(instance=administrativo)
        context = {
            'form': form,
            'administrativo': administrativo
        }
        return render(request, 'consultas/editar_administrativo.html', context)




@login_required
def administrativo_editar(request, pk):
        administrativo = get_object_or_404(Administrativo, pk=pk)

        if request.method == 'POST':
            form = AdministrativoForm(request.POST, instance=administrativo)
            if form.is_valid():
                form.save()
                messages.success(request, 'Cadastrado atualizado!')
               
                return redirect('administrativoListagem')
        else:
            form = AdministrativoForm(instance=administrativo)

        return render(request, 'consultas/editar_administrativo.html', {'form': form, 'administrativo': administrativo})


@require_POST
def administrativo_excluir(request, pk):
    administrativo = get_object_or_404(Administrativo, pk=pk)
    usuario = administrativo.usuario

    try:
        administrativo.delete()
        if usuario:
            usuario.delete()  # Exclui o usuário relacionado, se existir
        messages.success(request, 'Administrativo e usuário excluídos com sucesso')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('administrativoListagem')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        return render(request, 'consultas/excluir_administrativo.html', {'administrativo': administrativo})

# def administrativo_excluir(request, pk):
#     administrativo = get_object_or_404(Administrativo, pk=pk)

#     if request.method == 'POST':
#         administrativo.delete()
#         messages.error(request, 'Administrativo excluido')
        
#         return redirect('administrativoListagem')

#     return render(request, 'consultas/excluir_administrativo.html', {'administrativo': administrativo})

def is_profissionaldasaude(user):
    return user.groups.filter(name='profissionais de saude').exists()

@login_required
def listar_profissionaldasaude(request):
    profissionaldasaude = Profissionaldasaude.objects.all()
    form = ProfissionaldasaudeForm()
    return render(request, 'consultas/listagem_profissionaldasaude.html', {'profissionaldasaude': profissionaldasaude, 'form': form})

#modal
@login_required
def editar_profissionaldasaude(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("Recebendo POST request via AJAX")
        id = request.POST.get('id')
        print(f"ID recebido: {id}")
        profissionaldasaude = get_object_or_404(Profissionaldasaude, id=id)
        form = ProfissionaldasaudeForm(request.POST, instance=profissionaldasaude)
        if form.is_valid():
            form.save()
            print("Formulário válido e salvo com sucesso.")
            return JsonResponse({'success': True})
        else:
            print(f"Formulário inválido: {form.errors}")
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        print("Recebendo GET request")
        id = request.GET.get('id')
        profissionaldasaude = get_object_or_404(Profissionaldasaude, id=id)
        form = ProfissionaldasaudeForm(instance=profissionaldasaude)
        context = {
            'form': form,
            'profissionaldasaude': profissionaldasaude
        }
        return render(request, 'consultas/editar_profissionaldasaude.html', context)


@login_required
def profissionaldasaude_editar(request, pk):
    profissionaldasaude = get_object_or_404(Profissionaldasaude, pk=pk)

    if request.method == 'POST':
        form = ProfissionaldasaudeForm(request.POST, instance=profissionaldasaude)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cadastro atualizado.')
            return redirect('profissionaldasaudeListagem')
    else:
        form = ProfissionaldasaudeForm(instance=profissionaldasaude)

    return render(request, 'consultas/editar_proSaude.html', {'form': form, 'profissionaldasaude': profissionaldasaude})

@require_POST
def profissionaldasaude_excluir(request, pk):
    profissionaldasaude = get_object_or_404(Profissionaldasaude, pk=pk)
    usuario = profissionaldasaude.usuario

    try:
        profissionaldasaude.delete()
        if usuario:
            usuario.delete()
        messages.success(request, 'profissional da saude excluído')
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('profissionaldasaudeListagem')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        return render(request, 'consultas/excluir_proSaude.html', {'profissionaldasaude': profissionaldasaude})


# def profissionaldasaude_excluir(request, pk):
#     profissionaldasaude = get_object_or_404(Profissionaldasaude, pk=pk)

#     if request.method == 'POST':
#         profissionaldasaude.delete()
#         messages.error(request, 'Profissional de saúde excluido')
        
#         return redirect('profissionaldasaudeListagem')

#     return render(request, 'consultas/excluir_proSaude.html', {'profissionaldasaude': profissionaldasaude})



def listar_agendamentos(request):
    profissional_id = request.GET.get('profissional_saude')
    form = AgendamentoForm()
    profissionais_saude = Profissionaldasaude.objects.all()

     # Gera a lista de profissionais com nome completo
    profissionais_saude = Profissionaldasaude.objects.all()
    profissionais_saude_display = [
        {"id": profissional.id, "nome": profissional.get_display_name()}  
        for profissional in profissionais_saude
    ]

    # Filtro de agendamentos
    if profissional_id and profissional_id != 'todos':
        agendamentos = Agendamento.objects.filter(profissional_saude_id=profissional_id)
    else:
        agendamentos = Agendamento.objects.all()

    agendamentos_cancelados = agendamentos.filter(status_atendimento='cancelado')

    tolerancia = timedelta(seconds=10)
    now = timezone.now()

    for agendamento in agendamentos:
        if agendamento.status_atendimento == 'em_andamento' and not Atendimento.objects.filter(agendamento=agendamento).exists():
            if agendamento.inicio_atendimento and now - agendamento.inicio_atendimento > tolerancia:
                agendamento.status_atendimento = 'confirmado'
                agendamento.inicio_atendimento = None
                agendamento.save(update_fields=['status_atendimento', 'inicio_atendimento'])
            
    agendamentos = agendamentos.order_by('-data_agendamento')

    return render(request, 'consultas/listagem_agendamentos.html', {
        'agendamentos': agendamentos,
        'agendamentos_cancelados': agendamentos_cancelados,
        'profissionais_saude': profissionais_saude_display,
        'form': form
    })

def listar_agendamentos_cancelados(request):
    agendamentos_cancelados = Agendamento.objects.filter(status_atendimento='cancelado')
    data = [
        {
            'id': agendamento.id,
            'paciente': agendamento.paciente.nome,
            'data_agendamento': agendamento.data_agendamento.strftime('%d/%m/%Y'),
            'justificativa': agendamento.justificativa_cancelamento,
        }
        for agendamento in agendamentos_cancelados
    ]
    return JsonResponse({'cancelados': data})

    
def confirm_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    return render(request, 'consultas/confirm_agendamento.html', {'agendamento': agendamento})


def agendamento_confirmar(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)

    if agendamento.data_agendamento is None:
        messages.error(request, 'Data de agendamento não definida.')
        return redirect('agendamentoListagem')

    if agendamento.data_agendamento != timezone.now().date():
        messages.error(request, 'O agendamento só pode ser confirmado na data prevista.')
        return redirect('agendamentoListagem')

    agendamento.status_atendimento = 'confirmado'
    agendamento.horario_confirmacao = now()  # Registra o horário de confirmação
    agendamento.save()
    messages.success(request, 'Agendamento confirmado!')
    return redirect('agendamentoListagem')

def agendamento_ausente(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)
    agendamento.status_atendimento = 'ausente'
    agendamento.save()
    messages.warning(request, 'Agendamento definido como ausente!')
    return redirect('agendamentoListagem')



def reagendar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)

    if agendamento.status_atendimento != 'pendente':
        return JsonResponse({'success': False, 'errors': 'Este agendamento não pode ser reagendado porque não está pendente.'})

    if request.method == 'POST':
        form = AgendamentoReagendarForm(request.POST, instance=agendamento)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            errors = form.errors.get_json_data()
            return JsonResponse({'success': False, 'errors': errors})
    else:
        return JsonResponse({'success': False, 'errors': 'Método de requisição inválido.'})


@require_POST
def cancelar_agendamento(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, pk=agendamento_id)

    if agendamento.status_atendimento not in ['pendente', 'confirmado']:
        return JsonResponse({'success': False, 'errors': 'Não é possível cancelar um agendamento nesse status.'})

    justificativa = request.POST.get('justificativa', '').strip()

    if justificativa:
        agendamento.cancelar(justificativa)
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'errors': 'A justificativa é obrigatória.'})

        

class VisualizarAtendimentoView(DetailView):
    model = Atendimento
    template_name = 'consultas/visualizar_atendimento.html'
    context_object_name = 'atendimento'

    def dispatch(self, request, *args, **kwargs):
        atendimento = self.get_object()

        # Exibe no terminal o usuário logado
        # print(f"Usuário logado: {request.user.username} (ID: {request.user.id})")

        # Verifica se o usuário pertence ao grupo 'administradores' (acesso total)
        if request.user.groups.filter(name='administradores').exists():
            print("Usuário é administrador. Acesso concedido.")
            return super().dispatch(request, *args, **kwargs)

        # Verifica se o usuário pertence ao grupo 'administrativo'
        if request.user.groups.filter(name='administrativo').exists():
            print("Usuário pertence ao grupo 'administrativo'. Acesso negado.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'access_denied'}, status=403)
            else:
                return redirect('restricao_de_acesso')

        # Verifica se a consulta é privada
        if atendimento.privado:
            # Obtendo os médicos
            medico_responsavel = atendimento.medico_responsavel
            medico_logado = atendimento.medico_logado.usuario if atendimento.medico_logado else None

            # Exibe no terminal os médicos responsáveis
            # print(f"Médico responsável: {medico_responsavel.username} (ID: {medico_responsavel.id})")
            # if medico_logado:
            #     print(f"Médico logado: {medico_logado.username} (ID: {medico_logado.id})")
            # else:
            #     print("Médico logado não disponível (None)")

            # Verificação de permissão
            if request.user != medico_responsavel and request.user != medico_logado:
                print("Acesso negado - Usuário não é o médico responsável nem o médico logado.")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'access_denied'}, status=403)
                else:
                    return redirect('restricao_de_acesso')
            # else:
            #     print("Acesso concedido - Usuário é o médico responsável ou o médico logado.")

        return super().dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        atendimento = self.get_object()
        paciente = atendimento.agendamento.paciente

        # Buscar o atestado médico
        try:
            atestado = AtestadoMedico.objects.get(agendamento=atendimento.agendamento)
            if atestado.dias_afastamento == 0 and atestado.cid == 'N/A':
                atestado = None
        except AtestadoMedico.DoesNotExist:
            atestado = None

        # Buscar as receitas médicas
        receita_simples = ReceitaMedica.objects.filter(agendamento=atendimento.agendamento, tipo='simples').first()
        receita_controle_especial = ReceitaMedica.objects.filter(agendamento=atendimento.agendamento, tipo='controle_especial').first()

        # Buscar os laudos médicos
        laudos = Laudo.objects.filter(agendamento=atendimento.agendamento).order_by('-data_laudo')

        # Buscar os arquivos
        arquivos = ArquivoPaciente.objects.filter(paciente=paciente).order_by('-data_envio')

        # Verificar permissões
        user = self.request.user
        is_admin = user.groups.filter(name='administradores').exists()
        is_responsavel = user == atendimento.medico_responsavel
        is_logado = user == atendimento.medico_logado.usuario if atendimento.medico_logado else False

        user_has_permission = is_admin or is_responsavel or is_logado

        # Adicionar dados ao contexto
        context.update({
            'paciente': paciente,
            'atestado': atestado,
            'receita_simples': receita_simples,
            'receita_controle_especial': receita_controle_especial,
            'laudos': laudos,
            'arquivos': arquivos,
            'form': MultipleFileForm(),
            'user_has_permission': user_has_permission,  # Adicionar a permissão ao contexto
        })
        return context

    # Multiplos Arquivos
    def post(self, request, *args, **kwargs):
        atendimento = self.get_object()
        paciente = atendimento.agendamento.paciente

        if request.method == 'POST' and 'file_field' in request.FILES:
            form = MultipleFileForm(request.POST, request.FILES)
            if form.is_valid():
                files = request.FILES.getlist('file_field')
                for f in files:
                    ArquivoPaciente.objects.create(paciente=paciente, arquivo=f)

                messages.success(request, 'Enviado com sucesso!')
                return redirect('visualizarAtendimento', pk=atendimento.pk)
        # else:
        #     form = MultipleFileForm()
        return self.get(request, *args, **kwargs)


@csrf_exempt
def atualizar_privado(request, atendimento_id):
    if request.method == 'POST':
        atendimento = get_object_or_404(Atendimento, id=atendimento_id)
        user = request.user

        # Verificar permissões
        is_admin = user.groups.filter(name='administradores').exists()
        is_responsavel = user == atendimento.medico_responsavel
        is_logado = user == atendimento.medico_logado.usuario if atendimento.medico_logado else False

        if not (is_admin or is_responsavel or is_logado):
            return JsonResponse({'error': 'Permissão negada.'}, status=403)

        try:
            data = json.loads(request.body)
            atendimento.privado = data.get('privado', False)
            atendimento.save()
            return JsonResponse({'message': 'Privacidade atualizada com sucesso.'})
        except Exception as e:
            return JsonResponse({'error': 'Erro ao atualizar: ' + str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

# views.py

@login_required
def lista_atendimentos(request):
    atendimentos = Atendimento.objects.all()
    usuario_logado = request.user
    atendimentos_com_privacidade = [
        {
            'atendimento': atendimento,
            'is_private': atendimento.is_private_for_user(usuario_logado)
        }
        for atendimento in atendimentos
    ]
    return render(request, 'consultas/lista_atendimentos.html', {'atendimentos_com_privacidade': atendimentos_com_privacidade, 'usuario_logado': usuario_logado})


# def user_login(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(request, username=username, password=password)
#             if user:
#                 login(request, user)
#                 return redirect('home')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'consultas/login.html', {'form': form})


class PacienteCreate(CreateView):
    form_class = PacienteForm
    template_name = 'consultas/cadastro_paciente.html'
    success_url = reverse_lazy('pacienteListagem')

    def is_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def form_valid(self, form):
        cpf = form.cleaned_data['cpf']
        if Paciente.objects.filter(cpf=cpf).exists():
            if self.is_ajax():
                return JsonResponse({'success': False, 'errors': {'cpf': 'CPF já cadastrado. Por favor, utilize um CPF único.'}})
            messages.error(self.request, 'CPF já cadastrado. Por favor, utilize um CPF único.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, 'Paciente cadastrado com sucesso!')
        if self.is_ajax():
            return JsonResponse({'success': True, 'message': 'Paciente cadastrado com sucesso!'})
        return response

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({'success': False, 'errors': form.errors})
        messages.error(self.request, 'Erro ao cadastrar o paciente. Verifique os dados e tente novamente.')
        return super().form_invalid(form) 

class AdministrativoCreate(CreateView):
    model = Administrativo
    form_class = AdministrativoForm
    template_name = 'consultas/cadastro_administrativo.html'
    success_url = reverse_lazy('administrativoListagem')

    def is_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def form_valid(self, form):
        administrativo = form.save(commit=False)

        username = form.cleaned_data['cpf']
        email = form.cleaned_data['email']
        password = User.objects.make_random_password()

        if User.objects.filter(username=username).exists():
            if self.is_ajax():
                return JsonResponse({'success': False, 'errors': {'username': 'CPF já cadastrado como nome de usuário. Por favor, utilize um CPF único.'}})
            messages.error(self.request, 'CPF já cadastrado como nome de usuário. Por favor, utilize um CPF único.')
            return self.form_invalid(form)

        usuario = User.objects.create_user(username=username, email=email, password=password)

        administrativo.usuario = usuario
        administrativo.senha_gerada = password
        administrativo.save()

        grupo_administrativo = Group.objects.get(name='administrativo')
        usuario.groups.add(grupo_administrativo)

        # Gerando o link de redefinição de senha
        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        reset_url = self.request.build_absolute_uri(reverse('redefinir_senha_confirmacao', kwargs={'uidb64': uid, 'token': token}))

        # Enviar e-mail com o link de redefinição de senha
        assunto = 'Sistema Médico Pericial - UFAC - Confirmação de Cadastro'
        message = f'Olá {administrativo.nome}! Seu cadastro foi confirmado com sucesso! ' \
                  f'Seu login é o seu CPF. \n Por favor, clique no link abaixo para ' \
                  f'definir sua senha: \n {reset_url}'
        try:
            send_mail(assunto, message, EMAIL_HOST_USER, [email])
            msg = 'Cadastrado com sucesso! Enviamos um e-mail de recuperação de senha.'
        except:
            msg = 'Cadastro realizado com sucesso!'

        if self.is_ajax():
            return JsonResponse({'success': True, 'message': msg})

        messages.success(self.request, msg)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({'success': False, 'errors': form.errors})
        messages.error(self.request, 'Erro! Verifique os campos preenchidos e tente novamente.')
        return super().form_invalid(form)

class ProfissionaldasaudeCreate(CreateView):
    model = Profissionaldasaude
    form_class = ProfissionaldasaudeForm
    success_url = reverse_lazy('profissionaldasaudeListagem')

    def is_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def form_valid(self, form):
        profissional = form.save(commit=False)

        username = form.cleaned_data['cpf']
        email = form.cleaned_data['email']
        password = User.objects.make_random_password()

        if User.objects.filter(username=username).exists():
            if self.is_ajax():
                return JsonResponse({'success': False, 'errors': {'username': 'CPF já cadastrado como nome de usuário. Por favor, utilize um CPF único.'}})
            messages.error(self.request, 'CPF já cadastrado como nome de usuário. Por favor, utilize um CPF único.')
            return self.form_invalid(form)

        usuario = User.objects.create_user(username=username, email=email, password=password)

        profissional.usuario = usuario
        profissional.senha_gerada = password
        profissional.save()

        grupo_profissional = Group.objects.get(name='profissionais de saude')
        usuario.groups.add(grupo_profissional)

        # Gerando o link de redefinição de senha
        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        reset_url = self.request.build_absolute_uri(reverse('redefinir_senha_confirmacao', kwargs={'uidb64': uid, 'token': token}))

        # Enviar e-mail com o link de redefinição de senha
        assunto = 'Sistema Médico Pericial - UFAC - Confirmação de Cadastro'
        message = f'Olá {profissional.nome}! Seu cadastro foi confirmado com sucesso! ' \
                  f'Seu login é o seu CPF. \n Por favor, clique no link abaixo para ' \
                  f'definir sua senha: \n {reset_url}'
        try:
            send_mail(assunto, message, EMAIL_HOST_USER, [email])
            msg = 'Cadastrado com sucesso! Enviamos um e-mail de recuperação de senha.'
        except:
            msg = 'Cadastro realizado com sucesso!'

        if self.is_ajax():
            return JsonResponse({'success': True, 'message': msg})

        messages.success(self.request, msg)
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.is_ajax():
            return JsonResponse({'success': False, 'errors': form.errors})
        messages.error(self.request, 'Erro! Verifique os campos preenchidos e tente novamente.')
        return super().form_invalid(form)


# class AgendamentoCreate(CreateView):
#     model = Agendamento
#     form_class = AgendamentoForm
#     template_name = 'consultas/listagem_agendamentos.html'
#     success_url = reverse_lazy('agendamentoListagem')

#     def form_valid(self, form):
#         self.object = form.save()
#         agendamento_data = {
#             'paciente': self.object.paciente.nome,
#             'profissional_saude': self.object.profissional_saude.nome,
#             'data_agendamento': self.object.data_agendamento.strftime('%d/%m/%Y'),
#             'turno': self.object.get_turno_display(),
#             'prioridade_atendimento': 'Sim' if self.object.prioridade_atendimento else 'Não',
#             'download_url': reverse_lazy('downloadComprovante', kwargs={'pk': self.object.pk})
#         }
#         return JsonResponse({'success': True, 'agendamento': agendamento_data})

#     def form_invalid(self, form):
#         messages.error(self.request, 'Erro ao realizar o agendamento. Verifique os dados e tente novamente.')
#         print("Erro ao realizar o agendamento.")
#         print(form.errors)  

#         # Se a solicitação for AJAX, retorna um JSON com os erros
#         if self.request.is_ajax():
#             errors = form.errors.as_json()
#             return JsonResponse({'success': False, 'errors': errors}, status=400)

#         # Renderizar o template novamente com o formulário inválido
#         return self.render_to_response(self.get_context_data(form=form))
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['messages'] = messages.get_messages(self.request)
#         return context
    
#     def generate_pdf(self, agendamento):
#         html_content = render_to_string('consultas/comprovantePdf_agendamento.html', {'agendamento': agendamento})

#         pdf_file = io.BytesIO()
#         pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

#         if pisa_status.err:
#             raise Exception("Erro ao gerar PDF.")

#         pdf_file.seek(0)
#         return pdf_file
    
    
    
    
class AgendamentoCreate(CreateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = 'consultas/listagem_agendamentos.html'
    success_url = reverse_lazy('agendamentoListagem')

    def form_valid(self, form):
        self.object = form.save()
        agendamento_data = {
            'paciente': self.object.paciente.get_display_name(),
            'profissional_saude': self.object.profissional_saude.get_display_name(),
            'data_agendamento': self.object.data_agendamento.strftime('%d/%m/%Y'),
            'turno': self.object.get_turno_display(),
            'prioridade_atendimento': 'Sim' if self.object.prioridade_atendimento else 'Não',
            'download_url': reverse_lazy('downloadComprovante', kwargs={'pk': self.object.pk})
        }
        return JsonResponse({'success': True, 'agendamento': agendamento_data})

    def form_invalid(self, form):
        # Corrigindo a estrutura de retorno de erros para um objeto JSON adequado
        errors = form.errors.get_json_data()
        print(f"Erros no form_invalid: {errors}")
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['messages'] = messages.get_messages(self.request)
        return context




def download_comprovante(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk)

    # Renderiza o template para HTML
    html_content = render_to_string('pdfs/comprovantePdf_agendamento.html', {'agendamento': agendamento})

    # Gera o PDF usando Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    # Configura o PDF para download
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=Comprovante_Agendamento_{agendamento.id}.pdf'
    
    return response


@login_required
def criar_atendimento(request, agendamento_id):
    if request.method == 'POST':
        form = AtendimentoForm(request.POST)
        if form.is_valid():
            atendimento = form.save(commit=False)
            atendimento.agendamento_id = agendamento_id
            atendimento.save()
            messages.success(request, 'Atendimento criado com sucesso!')
            return redirect('listaAtendimentos')
    else:
        form = AtendimentoForm()

    return render(request, 'consultas/atendimento_form.html', {'form': form})



class AtendimentoCreate(CreateView):
    model = Atendimento
    form_class = AtendimentoForm
    template_name = 'consultas/atendimento.html'

    def dispatch(self, request, *args, **kwargs):
        # Verifica se o usuário pertence ao grupo 'administrativo'
        if request.user.groups.filter(name='administrativo').exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'access_denied'}, status=403)
            else:
                return redirect('restricao_de_acesso')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agendamento_id = self.kwargs['agendamento_id']
        agendamento = get_object_or_404(Agendamento, id=agendamento_id)
        context['agendamento'] = agendamento
        context['atestado_medico_form'] = AtestadoMedicoForm(agendamento=agendamento)
        context['receita_medica_form'] = ReceitaMedicaForm()
        context['laudo_form'] = LaudoForm(agendamento=agendamento)
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        agendamento_id = self.kwargs['agendamento_id']
        agendamento = get_object_or_404(Agendamento, id=agendamento_id)

        atendimento_existente = Atendimento.objects.filter(agendamento=agendamento).first()

        if atendimento_existente:
            messages.error(self.request, 'Já existe um atendimento para este agendamento.')
            return redirect('confirmar_atendimento', agendamento_id=agendamento.id)
        
        atendimento_form = AtendimentoForm(request.POST, request.FILES)
        atestado_medico_form = AtestadoMedicoForm(request.POST, agendamento=agendamento)
        receita_medica_form = ReceitaMedicaForm(request.POST, agendamento=agendamento)
        laudo_form = LaudoForm(request.POST, agendamento=agendamento)
        
        if atendimento_form.is_valid():
            return self.form_valid(atendimento_form, atestado_medico_form, receita_medica_form, laudo_form, agendamento)
        else:
            return self.form_invalid(atendimento_form, atestado_medico_form, receita_medica_form, laudo_form)

    def form_valid(self, atendimento_form, atestado_medico_form, receita_medica_form, laudo_form, agendamento):
        atendimento = atendimento_form.save(commit=False)
        atendimento.agendamento = agendamento
        atendimento.inicio_atendimento = agendamento.inicio_atendimento

        atendimento.medico_responsavel = agendamento.profissional_saude.usuario
        atendimento.medico_logado = Profissionaldasaude.objects.get(usuario=self.request.user)
        atendimento.fim_atendimento = timezone.now()
        atendimento.privado = 'privado' in self.request.POST
        atendimento.save()

        agendamento.status_atendimento = 'atendido'
        agendamento.save()

        if atestado_medico_form.is_valid():
            atestado_medico = atestado_medico_form.save(commit=False)
            dias_afastamento = atestado_medico_form.cleaned_data.get('dias_afastamento')
            texto_padrao = atestado_medico_form.cleaned_data.get('texto_padrao')
            if texto_padrao:
                atestado_medico.texto_padrao = texto_padrao.replace('[[DIAS]]', str(dias_afastamento))
            atestado_medico.agendamento = agendamento
            atestado_medico.save()

            if receita_medica_form.is_valid():
                receita_medica = receita_medica_form.save(commit=False)
                receita_medica.agendamento = agendamento
                receita_medica.save()

        if laudo_form.is_valid():
            laudo = laudo_form.save(commit=False)
            laudo.agendamento = agendamento
            laudo.save()

        return redirect('confirmar_atendimento', agendamento_id=agendamento.id)

    def form_invalid(self, atendimento_form, atestado_medico_form, receita_medica_form, laudo_form):
        context = self.get_context_data()
        context['form'] = atendimento_form
        context['atestado_medico_form'] = atestado_medico_form
        context['receita_medica_form'] = receita_medica_form
        context['laudo_form'] = laudo_form
        return self.render_to_response(context)

def registrar_inicio_atendimento(request, agendamento_id):
    if request.method == 'POST':
        try:
            agendamento = Agendamento.objects.get(id=agendamento_id)
            agendamento.inicio_atendimento = timezone.now()
            agendamento.status_atendimento = 'em_andamento'
            agendamento.save(update_fields=['inicio_atendimento', 'status_atendimento'])  # Força a atualização
            print(f"Início do atendimento registrado para {agendamento.id}")
            return JsonResponse({'status': 'success'})
        except Agendamento.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Agendamento não encontrado.'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=400)

def manter_em_atendimento(request, agendamento_id):
    if request.method == 'POST':
        try:
            agendamento = Agendamento.objects.get(id=agendamento_id)
            agendamento.status_atendimento = 'em_andamento'
            agendamento.save()
            return JsonResponse({'status': 'success'})
        except Agendamento.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Agendamento não encontrado.'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Método inválido.'}, status=400)

def confirmar_atendimento(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    atendimento = get_object_or_404(Atendimento, agendamento=agendamento)

    # Salvar o fim do atendimento, se ainda não estiver definido
    if not atendimento.fim_atendimento:
        atendimento.fim_atendimento = timezone.now()
        atendimento.save()

    # Buscar as receitas médicas
    receita_simples = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='simples').first()
    receita_controle_especial = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='controle_especial').first()

    laudos = Laudo.objects.filter(agendamento=agendamento).order_by('-data_laudo')

    # Verificar se os campos essenciais estão preenchidos
    mostrar_receita_simples = receita_simples and (receita_simples.prescricao or receita_simples.dosagem or receita_simples.via_administrativa or receita_simples.modo_uso)
    mostrar_receita_controle_especial = receita_controle_especial and (receita_controle_especial.prescricao or receita_controle_especial.dosagem or receita_controle_especial.via_administrativa or receita_controle_especial.modo_uso)

    return render(request, 'consultas/confirmar_atendimento.html', {
        'atendimento': atendimento,
        'receita_simples': receita_simples if mostrar_receita_simples else None,
        'receita_controle_especial': receita_controle_especial if mostrar_receita_controle_especial else None,
        'laudos': laudos,
    })
    
@require_POST
def cancelar_atendimento(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)

    if agendamento.status_atendimento not in ['confirmado', 'em_andamento']:
        return JsonResponse({'success': False, 'errors': 'Este atendimento não pode ser cancelado.'})

    justificativa = request.POST.get('justificativa', '').strip()

    if not justificativa:
        return JsonResponse({'success': False, 'errors': 'A justificativa é obrigatória.'})

    agendamento.status_atendimento = 'cancelado'
    agendamento.justificativa_cancelamento = justificativa
    agendamento.horario_cancelamento = timezone.now()
    agendamento.save()

    return JsonResponse({'success': True})


def download_comprovante_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)

    # Renderiza o template para HTML
    html_content = render_to_string('pdfs/comprovantePdf_atendimento.html', {'atendimento': atendimento})

    # Gera o PDF usando Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    # Configura o PDF para download
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=comprovante_atendimento_{atendimento_id}.pdf'
    
    return response

def obter_relatorios(request):
    # Dados principais do relatório
    total_atendimentos = Agendamento.objects.filter(status_atendimento='atendido').count()
    total_cancelados = Agendamento.objects.filter(status_atendimento='cancelado').count()
    pacientes_atendidos = Paciente.objects.filter(
        agendamento__status_atendimento='atendido'
    ).distinct()
    atendimentos_por_turno = Agendamento.objects.values('turno').annotate(total=Count('id'))
    
    # Dados organizados para retorno
    relatorio_dados = {
        'total_atendimentos': total_atendimentos,
        'total_cancelados': total_cancelados,
        'pacientes_atendidos': [paciente.nome for paciente in pacientes_atendidos],
        'atendimentos_por_turno': {item['turno']: item['total'] for item in atendimentos_por_turno},
    }

    # Se for um pedido AJAX, retornar JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(relatorio_dados)
    
    return render(request, 'relatorio.html', {'relatorio_dados': relatorio_dados})

def visualizar_pdf_exames(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)

    # Verifica se o atendimento possui um PDF de exames
    if atendimento.pdf_exames:
        pdf_file_path = atendimento.pdf_exames.path
        with open(pdf_file_path, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'filename=pdf_exames_atendimento_{atendimento_id}.pdf'
            return response
    else:
        # Caso não tenha PDF de exames, você pode retornar uma mensagem de erro ou redirecionar para outra página
        return HttpResponse("PDF de exames não encontrado.")
  
    
def visualizar_comprovante_atendimento(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)

    # Renderiza o template para HTML
    html_content = render_to_string('pdfs/comprovantePdf_atendimento.html', {'atendimento': atendimento})

    # Gera o PDF usando Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    # Configura o PDF para visualização
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=comprovante_atendimento_{atendimento_id}.pdf'
    
    return response


# def filtrar_prontuarios(request):
#     paciente_id = request.GET.get('paciente_id')
#     medicos_ids = request.GET.getlist('medicos')

#     paciente = get_object_or_404(Paciente, pk=paciente_id)
#     ids_agendamentos = paciente.agendamento_set.all().values_list('id', flat=True)

#     atendimentos = Atendimento.objects.filter(agendamento__id__in=ids_agendamentos, agendamento__profissional_saude__id__in=medicos_ids)

#     # Serializa os objetos com representação natural de chaves estrangeiras
#     data = serialize('json', atendimentos, use_natural_foreign_keys=True, fields=('profissional_saude', 'paciente', 'data_atendimento', 'anamnese', 'exame_fisico', 'exames_complementares', 'diagnostico', 'conduta'))
#     return HttpResponse(data, content_type='application/json')


def prontuario_medico(request, paciente_id):
    # Verifica se o usuário pertence ao grupo 'administrativo' (sem acesso)
    if request.user.groups.filter(name='administrativo').exists():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'access_denied'}, status=403)
        else:
            return redirect('restricao_de_acesso')  # Página ou modal de restrição de acesso

    # Verifica se o usuário pertence ao grupo 'administradores' (acesso total)
    tem_acesso_total = request.user.groups.filter(name='administradores').exists()

    paciente = Paciente.objects.get(pk=paciente_id)
    atendimentos = Atendimento.objects.filter(agendamento__paciente=paciente)
    profissionais_saude = Profissionaldasaude.objects.all()

    prontuario_dados = []
    for atendimento in atendimentos:
        agendamento = atendimento.agendamento
        receita_simples = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='simples').first()
        receita_controle_especial = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='controle_especial').first()
        laudos = Laudo.objects.filter(agendamento=agendamento).order_by('-data_laudo')

        mostrar_receita_simples = receita_simples and (
            receita_simples.prescricao or receita_simples.dosagem or receita_simples.via_administrativa or receita_simples.modo_uso
        )
        mostrar_receita_controle_especial = receita_controle_especial and (
            receita_controle_especial.prescricao or receita_controle_especial.dosagem or receita_controle_especial.via_administrativa or receita_controle_especial.modo_uso
        )

        # Verifica se o atendimento é privado e se o usuário tem acesso
        if atendimento.privado:
            medico_responsavel = atendimento.medico_responsavel
            medico_logado = atendimento.medico_logado.usuario if atendimento.medico_logado else None

            if not tem_acesso_total and request.user != medico_responsavel and request.user != medico_logado:
                prontuario_dados.append({
                    'privado': True,
                    'atendimento': atendimento,
                })
                continue

        # Adiciona os dados do atendimento ao prontuário
        prontuario_dados.append({
            'privado': False,
            'atendimento': atendimento,
            'medico_responsavel': atendimento.medico_responsavel,
            'medico_logado': atendimento.medico_logado.nome if atendimento.medico_logado else None,
            'receita_simples': receita_simples if mostrar_receita_simples else None,
            'receita_controle_especial': receita_controle_especial if mostrar_receita_controle_especial else None,
            'laudos': laudos,
        })

    return render(request, 'consultas/prontuario_medico.html', {
        'paciente': paciente,
        'prontuario_dados': prontuario_dados,
        'profissionais_saude': profissionais_saude,
    })


def filtrar_prontuarios(request):
    paciente_id = request.GET.get('paciente_id')
    medicos_ids = request.GET.getlist('medicos')

    paciente = get_object_or_404(Paciente, pk=paciente_id)
    ids_agendamentos = paciente.agendamento_set.all().values_list('id', flat=True)

    tem_acesso_total = request.user.groups.filter(name='administradores').exists()

    if not medicos_ids:  # Se nenhum médico foi selecionado, retornar todos os atendimentos
        atendimentos = Atendimento.objects.filter(agendamento__paciente=paciente)
    else:
        atendimentos = Atendimento.objects.filter(
            agendamento__id__in=ids_agendamentos, 
            agendamento__profissional_saude__id__in=medicos_ids
        )

    atendimentos_list = []
    for atendimento in atendimentos:
        # Lógica para atender a restrição de atendimentos privados
        if atendimento.privado:
            medico_responsavel = atendimento.medico_responsavel
            medico_logado = atendimento.medico_logado.usuario if atendimento.medico_logado else None

            if not tem_acesso_total and request.user != medico_responsavel and request.user != medico_logado:
                atendimentos_list.append({
                    'privado': True,  # Indica que este atendimento é privado
                })
                continue

        # Adiciona os dados do atendimento acessível
        atendimento_dict = {
            'privado': False,  # Indica que este atendimento não é privado
            'profissional_saude': atendimento.agendamento.profissional_saude.nome,
            'area': atendimento.agendamento.profissional_saude.area,
            'paciente': atendimento.agendamento.paciente.nome,
            'data_atendimento': atendimento.data_atendimento.strftime('%d-%m-%Y'),  # Formatar a data para string
            'anamnese': atendimento.anamnese,
            'exame_fisico': atendimento.exame_fisico,
            'exames_complementares': atendimento.exames_complementares,
            'diagnostico': atendimento.diagnostico,
            'conduta': atendimento.conduta,
        }
        atendimentos_list.append(atendimento_dict)

    return JsonResponse(atendimentos_list, safe=False)

# def pdf_prontuario_medico(request, paciente_id):
#     paciente = Paciente.objects.get(pk=paciente_id)
#     paciente_nome = paciente.nome.replace(' ', '_').lower()
#     medicos_ids = request.GET.get('medicos')
#     atendimentos_ids = request.GET.get('atendimentos')

#     if medicos_ids:
#         medicos_ids = [int(id) for id in medicos_ids.split(",")]

#         ids_agendamentos = paciente.agendamento_set.filter(profissional_saude__id__in=medicos_ids).values_list('id', flat=True)
#         atendimentos = Atendimento.objects.filter(agendamento__id__in=ids_agendamentos)
#     else:
#         atendimentos = Atendimento.objects.filter(agendamento__paciente=paciente)

#     if atendimentos_ids:
#         atendimentos_ids = [int(id) for id in atendimentos_ids.split(",")]
#         atendimentos = atendimentos.filter(id__in=atendimentos_ids)

#     prontuario_dados = []
#     for atendimento in atendimentos:
#         agendamento = atendimento.agendamento
#         receita_simples = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='simples').first()
#         receita_controle_especial = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='controle_especial').first()

#         mostrar_receita_simples = receita_simples and (
#             receita_simples.prescricao or receita_simples.dosagem or receita_simples.via_administrativa or receita_simples.modo_uso
#         )
#         mostrar_receita_controle_especial = receita_controle_especial and (
#             receita_controle_especial.prescricao or receita_controle_especial.dosagem or receita_controle_especial.via_administrativa or receita_controle_especial.modo_uso
#         )

#         prontuario_dados.append({
#             'atendimento': atendimento,
#             'receita_simples': receita_simples if mostrar_receita_simples else None,
#             'receita_controle_especial': receita_controle_especial if mostrar_receita_controle_especial else None,
#         })

#     context = {
#         'paciente': paciente,
#         'prontuario_dados': prontuario_dados,
#         'medicos_ids': medicos_ids,
#     }

#     html = render_to_string('pdfs/pdf_prontuario_medico.html', context)

#     # WeasyPrint para transformar o HTML em PDF.
#     pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()

#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="prontuario_{paciente_nome}.pdf"'
#     return response

def pdf_prontuario_medico(request, paciente_id):
    paciente = Paciente.objects.get(pk=paciente_id)
    paciente_nome = paciente.nome.replace(' ', '_').lower()
    medicos_ids = request.GET.get('medicos')
    atendimentos_ids = request.GET.get('atendimentos')

    if medicos_ids:
        medicos_ids = [int(id) for id in medicos_ids.split(",")]
        ids_agendamentos = paciente.agendamento_set.filter(profissional_saude__id__in=medicos_ids).values_list('id', flat=True)
        atendimentos = Atendimento.objects.filter(agendamento__id__in=ids_agendamentos)
    else:
        atendimentos = Atendimento.objects.filter(agendamento__paciente=paciente)

    if atendimentos_ids:
        atendimentos_ids = [int(id) for id in atendimentos_ids.split(",")]
        atendimentos = atendimentos.filter(id__in=atendimentos_ids)

    prontuario_dados = []
    for atendimento in atendimentos:
        agendamento = atendimento.agendamento
        receita_simples = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='simples').first()
        receita_controle_especial = ReceitaMedica.objects.filter(agendamento=agendamento, tipo='controle_especial').first()

        mostrar_receita_simples = receita_simples and (
            receita_simples.prescricao or receita_simples.dosagem or receita_simples.via_administrativa or receita_simples.modo_uso
        )
        mostrar_receita_controle_especial = receita_controle_especial and (
            receita_controle_especial.prescricao or receita_controle_especial.dosagem or receita_controle_especial.via_administrativa or receita_controle_especial.modo_uso
        )

        prontuario_dados.append({
            'atendimento': atendimento,
            'receita_simples': receita_simples if mostrar_receita_simples else None,
            'receita_controle_especial': receita_controle_especial if mostrar_receita_controle_especial else None,
        })

    context = {
        'paciente': paciente,
        'prontuario_dados': prontuario_dados,
        'medicos_ids': medicos_ids,
    }

    html = render_to_string('pdfs/pdf_prontuario_medico.html', context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="prontuario_{paciente_nome}.pdf"'
    return response


def pdf_atestado_medico(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)
    agendamento = atendimento.agendamento
    atestado = get_object_or_404(AtestadoMedico, agendamento=agendamento)
    paciente_nome = atestado.paciente.nome.replace(' ', '_').lower()
    
    context = {
        'atendimento': atendimento,
        'atestado': atestado,
    }

    html = render_to_string('pdfs/pdf_atestado_medico.html', context)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="atestado_{paciente_nome}.pdf"'
    return response

def pdf_receita_medica(request, atendimento_id, tipo=None):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)
    agendamento = atendimento.agendamento
    receita = get_object_or_404(ReceitaMedica, agendamento=agendamento)
    paciente_nome = receita.paciente.nome.replace(' ', '_').lower()

    context = {
        'atendimento': atendimento,
        'receita': receita,
    }

    # Verifica o tipo de receita para escolher o template correto
    if tipo == 'controle_especial' or receita.tipo == 'controle_especial':
        template_path = 'pdfs/pdf_receita_medica_controle.html'
    else:
        template_path = 'pdfs/pdf_receita_medica.html'

    html = render_to_string(template_path, context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receita_{paciente_nome}.pdf"'
    return response

def pdf_laudo_medico(request, atendimento_id):
    atendimento = get_object_or_404(Atendimento, id=atendimento_id)
    agendamento = atendimento.agendamento
    laudo = get_object_or_404(Laudo, agendamento=agendamento)
    paciente_nome = laudo.paciente.nome.replace(' ', '_').lower()

    context = {
        'atendimento': atendimento,
        'laudo': laudo,
    }

    html = render_to_string('pdfs/pdf_laudo_medico.html', context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo da página
        pdf_content = page.pdf(format='A4', print_background=True)

        browser.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="laudo_{paciente_nome}.pdf"'
    return response

def pdf_comprovante_cancelamento(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)

    # Registra o horário de cancelamento se ainda não estiver registrado
    if not agendamento.horario_cancelamento:
        agendamento.horario_cancelamento = timezone.now()
        agendamento.save()

    context = {
        'agendamento': agendamento,
        'justificativa': agendamento.justificativa_cancelamento or 'Não informada',
        'horario_cancelamento': agendamento.horario_cancelamento,
        'horario_confirmacao': agendamento.horario_confirmacao,
    }

    # Renderiza o HTML com o contexto
    html = render_to_string('pdfs/comprovantePdf_cancelamento.html', context)

    # Gera o PDF usando Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_load_state('networkidle')  # Espera o carregamento completo
        pdf_content = page.pdf(format='A4', print_background=True)
        browser.close()

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="comprovante_cancelamento_{agendamento_id}.pdf"'
    return response

# def pdf_atestado_medico(request, atendimento_id):
#     atendimento = get_object_or_404(Atendimento, id=atendimento_id)
#     agendamento = atendimento.agendamento
#     atestado = get_object_or_404(AtestadoMedico, agendamento=agendamento)
#     paciente_nome = atestado.paciente.nome.replace(' ', '_').lower()
    
#     context = {
#         'atendimento': atendimento,
#         'atestado': atestado,
#     }

#     html = render_to_string('pdfs/pdf_atestado_medico.html', context)
    
#     # Cria um arquivo temporário
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
#         HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(target=temp_pdf.name)
        
#         # Lê o conteúdo do arquivo temporário
#         temp_pdf.seek(0)
#         pdf_content = temp_pdf.read()

#     # Remove o arquivo temporário
#     os.remove(temp_pdf.name)
    
#     response = HttpResponse(pdf_content, content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="atestado_{paciente_nome}.pdf"'
#     return response

# def pdf_receita_medica(request, atendimento_id, tipo=None):
#     atendimento = get_object_or_404(Atendimento, id=atendimento_id)
#     agendamento = atendimento.agendamento
#     receita = get_object_or_404(ReceitaMedica, agendamento=agendamento)
#     paciente_nome = receita.paciente.nome.replace(' ', '_').lower()

#     context = {
#         'atendimento': atendimento,
#         'receita': receita,
#     }

#     # Verifica o tipo de receita para escolher o template correto
#     if tipo == 'controle_especial' or receita.tipo == 'controle_especial':
#         template_path = 'pdfs/pdf_receita_medica_controle.html'
#         css = CSS(string='@page { size: A4 landscape; }')
#     else:
#         template_path = 'pdfs/pdf_receita_medica.html'
#         css = None

#     html = render_to_string(template_path, context)
    
#     # Cria um arquivo temporário
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
#         HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(target=temp_pdf.name, stylesheets=[css] if css else [])
        
#         # Lê o conteúdo do arquivo temporário
#         temp_pdf.seek(0)
#         pdf_content = temp_pdf.read()

#     # Remove o arquivo temporário
#     os.remove(temp_pdf.name)
    
#     response = HttpResponse(pdf_content, content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="receita_{paciente_nome}.pdf"'
#     return response


# def pdf_laudo_medico(request, atendimento_id):
#     atendimento = get_object_or_404(Atendimento, id=atendimento_id)
#     agendamento = atendimento.agendamento
#     laudo = get_object_or_404(Laudo, agendamento=agendamento)
#     paciente_nome = laudo.paciente.nome.replace(' ', '_').lower()
    
#     context = {
#         'atendimento': atendimento,
#         'laudo': laudo,
#     }

#     html = render_to_string('pdfs/pdf_laudo_medico.html', context)
    
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
#         HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(target=temp_pdf.name)
        
#         temp_pdf.seek(0)
#         pdf_content = temp_pdf.read()

#     os.remove(temp_pdf.name)
    
#     response = HttpResponse(pdf_content, content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="laudo_{paciente_nome}.pdf"'
#     return response


def restricao_de_acesso(request):
    return render(request, 'consultas/restricao.html')


def excluir_arquivo(request, arquivo_id, atendimento_id):
    arquivo = get_object_or_404(ArquivoPaciente, id=arquivo_id)

    if request.method == 'POST':
        arquivo.delete()
        messages.success(request, 'Arquivo excluído!')
        return redirect('visualizarAtendimento', pk=atendimento_id)

    else:
        messages.error(request, 'Falha ao excluir o arquivo! Tente novamente.')

    return redirect('visualizarAtendimento', pk=atendimento_id)


def search_paciente(request):
    query = request.GET.get('q', '')
    pacientes = Paciente.objects.filter(nome__icontains=query)[:10]  # Limitar a 10 resultados
    results = [{'id': paciente.id, 'nome': paciente.get_display_name()} for paciente in pacientes]
    return JsonResponse(results, safe=False)

def search_profissional(request):
    query = request.GET.get('q', '')
    profissionais = Profissionaldasaude.objects.filter(nome__icontains=query)[:10]  # Limitar a 10 resultados
    results = [{'id': profissional.id, 'nome': profissional.get_display_name()} for profissional in profissionais]
    return JsonResponse(results, safe=False)